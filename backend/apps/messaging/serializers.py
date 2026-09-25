from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.catalog.serializers import ProductListSerializer
from apps.media.serializers import MessageAttachmentSerializer

from .models import Conversation, Message

# What the conversation list shows instead of a body, per message type.
TYPE_PREVIEW = {
    Message.Type.AUDIO: "🎙️ Message vocal",
    Message.Type.IMAGE: "🖼️ Photo",
    Message.Type.VIDEO: "🎥 Vidéo",
    Message.Type.PRODUCT: "📎 Annonce jointe",
}


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    shared_product = ProductListSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "conversation", "sender", "message_type", "body", "shared_product",
            "attachments", "created_at", "read_at", "is_mine",
        ]
        read_only_fields = ["conversation", "sender", "created_at", "read_at"]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Text and product only — files arrive as separate multipart parts.

    A `ListField` of files would make DRF hold every upload in memory before
    the first validation; the view reads them from `request.FILES` and hands
    them to `apps.media.services`, which validates each one before storing.
    """

    class Meta:
        model = Message
        fields = ["id", "body", "shared_product"]


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    initial_product = ProductListSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "other_participant", "initial_product", "last_message", "unread_count", "updated_at"]

    def get_other_participant(self, obj):
        request = self.context.get("request")
        other = obj.other_participant(request.user)
        return UserPublicSerializer(other, context=self.context).data

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        preview = TYPE_PREVIEW.get(last.message_type) or last.body or ""
        return {
            "body": preview,
            "created_at": last.created_at,
            "is_mine": self.context["request"].user.id == last.sender_id,
        }

    def get_unread_count(self, obj):
        request = self.context.get("request")
        return obj.messages.filter(read_at__isnull=True).exclude(sender=request.user).count()
