from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer
from .services import mark_all_read, unread_count_for


class NotificationViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    # For the schema generator only; get_queryset() scopes to the requester.
    queryset = Notification.objects.none()

    def get_queryset(self):
        # Always scoped to the requester — never another user's notifications.
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(read_at__isnull=True)
        return qs

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread_count": unread_count_for(request.user)})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = mark_all_read(request.user)
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)


class DeviceTokenViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Les appareils à prévenir quand l'application est fermée.

    Un jeton Firebase désigne une installation, pas une personne. Deux
    comptes sur le même téléphone donnent le même jeton : l'enregistrer
    doit donc **réaffecter** la ligne, jamais en créer une seconde, sans
    quoi les notifications de l'un partiraient aussi chez l'autre.

    Le lookup se fait sur le jeton lui-même, pas sur un identifiant de
    ligne : l'application connaît son jeton, pas notre clé primaire.
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "token"
    # Le lookup par défaut refuserait les caractères d'un jeton FCM.
    lookup_value_regex = "[^/]+"
    queryset = DeviceToken.objects.none()

    def get_queryset(self):
        # Supprimer se limite à ses propres appareils : sans ce filtre,
        # connaître le jeton de quelqu'un suffirait à le faire taire.
        return DeviceToken.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, _created = DeviceToken.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={
                "user": request.user,
                "platform": serializer.validated_data.get(
                    "platform", DeviceToken.Platform.ANDROID
                ),
            },
        )
        return Response(
            DeviceTokenSerializer(device).data, status=status.HTTP_201_CREATED
        )
