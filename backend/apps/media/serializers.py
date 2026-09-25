from rest_framework import serializers

from .models import MessageAttachment


class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = [
            "id", "kind", "status", "url", "poster_url",
            "mime_type", "size", "width", "height", "duration",
        ]

    def _api_url(self, obj, suffix=""):
        """Media is served by the API, never by a storage URL.

        A conversation is private: handing out a bucket link would make its
        contents readable by anyone who gets that link, for as long as the
        object exists. Membership is checked on every request instead.
        """
        request = self.context.get("request")
        path = (
            f"/api/v1/conversations/{obj.message.conversation_id}"
            f"/messages/{obj.message_id}/attachments/{obj.pk}/{suffix}"
        )
        return request.build_absolute_uri(path) if request else path

    def get_url(self, obj):
        return self._api_url(obj)

    def get_poster_url(self, obj):
        return self._api_url(obj, "poster/") if obj.poster else None
