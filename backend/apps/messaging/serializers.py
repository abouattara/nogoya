from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.catalog.serializers import ProductListSerializer
from apps.media.serializers import MessageAttachmentSerializer

from .models import Conversation, Message
from .services import member_of, support_account

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
        """Ce message est-il de celui qui lit ?

        Pour un membre, la question est simple. Pour l'équipe, non : ses
        réponses partent au nom du compte de service, pas du sien. Comparer
        au seul `request.user` rendait donc **tous** les messages « pas de
        moi » côté équipe — ses propres réponses comme celles du membre —
        et la conversation s'affichait d'une seule couleur, illisible.
        Côté membre, la même conversation paraissait normale.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # Une note de service n'appartient à personne : l'attribuer au
        # client faisait passer le récapitulatif d'une demande pour un
        # message qu'il aurait écrit.
        if obj.message_type == Message.Type.SYSTEM:
            return False
        if request.user.is_staff:
            return obj.sender_id == support_account().pk
        return obj.sender_id == request.user.id


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
        fields = [
            "id", "other_participant", "initial_product", "last_message",
            "unread_count", "audience", "updated_at",
        ]

    def get_other_participant(self, obj):
        """Qui le lecteur a en face de lui.

        Un membre a toujours NOGOYA en face : c'est la promesse du schéma
        intermédié, et afficher le nom de la personne de permanence la
        romprait. L'équipe, elle, a besoin de savoir à qui elle parle.
        """
        request = self.context.get("request")
        member = member_of(obj)
        if request and request.user.is_staff:
            return UserPublicSerializer(member, context=self.context).data
        return UserPublicSerializer(support_account(), context=self.context).data

    def _voice_of(self, request):
        """Sous quelle identité ce lecteur écrit dans le fil.

        L'équipe répond au nom du compte de service, pas du sien. Comparer
        au seul `request.user` revenait à dire qu'aucun message n'était
        d'elle : ses propres réponses rentraient dans son compteur de non
        lus, et l'aperçu du fil perdait son « Vous : ». Le fil remontait
        donc en tête avec une pastille, pour une phrase qu'elle venait
        d'écrire.
        """
        if not request or not request.user.is_authenticated:
            return None
        return support_account().pk if request.user.is_staff else request.user.id

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        preview = TYPE_PREVIEW.get(last.message_type) or last.body or ""
        voice = self._voice_of(self.context.get("request"))
        return {
            "body": preview,
            "created_at": last.created_at,
            # Une note de service n'est de personne : elle ne prend pas le
            # « Vous : » de celui qui la lit.
            "is_mine": last.message_type != Message.Type.SYSTEM and last.sender_id == voice,
        }

    def get_unread_count(self, obj):
        voice = self._voice_of(self.context.get("request"))
        if voice is None:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender_id=voice).count()
