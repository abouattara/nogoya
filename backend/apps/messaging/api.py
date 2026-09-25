from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, parsers, permissions, renderers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Product
from apps.media.models import MessageAttachment
from apps.media.services import build_attachments
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Conversation, ConversationBlock, Message, MessageReport
from .permissions import IsConversationParticipant
from .serializers import (
    TYPE_PREVIEW,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from .services import get_or_create_conversation, mark_read, participant_filter, unread_count_for

User = get_user_model()



class MediaRenderer(renderers.BaseRenderer):
    """Accepts any `Accept` header on the media endpoints.

    DRF negotiates the renderer *before* the view runs, so a player asking
    for `Accept: audio/*` (or an <img> asking for `image/*`) got a 406 from
    an endpoint that returns nothing else. The view answers with a
    FileResponse, so this renderer never actually renders anything.
    """

    media_type = "*/*"
    format = "media"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ConversationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    # Only so the schema generator can find the model: the real rows always
    # come from get_queryset(), scoped to the requester.
    queryset = Conversation.objects.none()

    def get_queryset(self):
        return Conversation.objects.filter(participant_filter(self.request.user)).select_related(
            "participant_low", "participant_high", "initial_product"
        )

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")
        product = get_object_or_404(Product, pk=product_id, status=Product.Status.APPROVED, is_active=True)
        supplier_user = product.supplier.user
        if supplier_user.id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas démarrer une conversation avec vous-même."}, status=status.HTTP_400_BAD_REQUEST)
        conversation, _created = get_or_create_conversation(request.user, supplier_user, product=product)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get", "post"],
        parser_classes=[parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser],
    )
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == "POST":
            if conversation.blocks.exists():
                return Response(
                    {"detail": "Cette conversation est bloquée."}, status=status.HTTP_403_FORBIDDEN
                )
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            images = request.FILES.getlist("images")
            videos = request.FILES.getlist("videos")
            audios = request.FILES.getlist("audios")
            posters = request.FILES.getlist("posters")
            durations = request.data.getlist("durations") if hasattr(request.data, "getlist") else []

            if not any([serializer.validated_data.get("body"), serializer.validated_data.get("shared_product"), images, videos, audios]):
                return Response(
                    {"detail": "Un message doit contenir du texte, un fichier ou une annonce jointe."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # One transaction: a message that kept only three of its four
                # photos would be worse than one that was refused outright.
                with transaction.atomic():
                    message = serializer.save(conversation=conversation, sender=request.user)
                    build_attachments(
                        message,
                        images=images,
                        videos=videos,
                        audios=audios,
                        posters=posters,
                        durations=durations,
                    )
                    message.sync_type()
            except DjangoValidationError as exc:
                return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

            Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
            message = (
                Message.objects.prefetch_related("attachments")
                .select_related("sender", "shared_product")
                .get(pk=message.pk)
            )
            self._notify_recipient(conversation, message)
            return Response(
                MessageSerializer(message, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        page = self.paginate_queryset(
            conversation.messages.select_related("sender", "shared_product").prefetch_related("attachments")
        )
        serializer = MessageSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    def _notify_recipient(self, conversation, message):
        recipient = conversation.other_participant(message.sender)
        sender_name = message.sender.get_full_name() or message.sender.phone
        preview = TYPE_PREVIEW.get(message.message_type) or message.body[:120] or "📎 Annonce jointe"
        notify(
            recipient,
            type=Notification.Type.NEW_MESSAGE,
            title=f"Nouveau message de {sender_name}",
            message=preview,
            url=f"/compte/messages/{conversation.pk}",
            data={"conversation_id": conversation.pk, "message_id": message.pk},
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="messages/(?P<message_pk>[^/.]+)/attachments/(?P<attachment_pk>[^/.]+)",
        renderer_classes=[MediaRenderer],
    )
    def attachment(self, request, pk=None, message_pk=None, attachment_pk=None):
        """Serve one attachment — only to the two participants.

        The bytes always go through this view, whatever the storage backend.
        We deliberately do *not* redirect to a storage URL: product images
        live under a public prefix, and a bucket link to a private photo or
        voice note would stay readable by anyone holding it for as long as
        the object exists. `get_object()` has already rejected anyone outside
        the conversation.
        """
        return self._serve(request, message_pk, attachment_pk, field="file")

    @action(
        detail=True,
        methods=["get"],
        url_path="messages/(?P<message_pk>[^/.]+)/attachments/(?P<attachment_pk>[^/.]+)/poster",
        renderer_classes=[MediaRenderer],
    )
    def attachment_poster(self, request, pk=None, message_pk=None, attachment_pk=None):
        """The still frame / thumbnail, so a conversation can be scanned
        without downloading a single video."""
        return self._serve(request, message_pk, attachment_pk, field="poster")

    def _serve(self, request, message_pk, attachment_pk, field):
        conversation = self.get_object()  # 404s for non-participants
        attachment = get_object_or_404(
            MessageAttachment,
            pk=attachment_pk,
            message__pk=message_pk,
            message__conversation=conversation,
        )
        stored = getattr(attachment, field)
        if not stored:
            raise Http404

        content_type = attachment.mime_type if field == "file" else "image/jpeg"
        response = FileResponse(stored.open("rb"), content_type=content_type or "application/octet-stream")
        # Private to this reader: a shared cache must never keep it, and the
        # browser may reuse it for the session since the bytes never change.
        response["Cache-Control"] = "private, max-age=3600"
        return response

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self.get_object()
        mark_read(conversation, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        conversation = self.get_object()
        ConversationBlock.objects.get_or_create(conversation=conversation, blocked_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread_count": unread_count_for(request.user)})


class MessageReportView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        message_id = request.data.get("message")
        message = get_object_or_404(Message, pk=message_id)
        if not message.conversation.has_participant(request.user):
            return Response(status=status.HTTP_404_NOT_FOUND)
        MessageReport.objects.create(
            message=message, reported_by=request.user, reason=request.data.get("reason", "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
