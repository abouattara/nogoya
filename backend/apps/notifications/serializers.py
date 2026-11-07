from rest_framework import serializers

from .models import DeviceToken, Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "type", "title", "message", "url", "data", "is_read", "read_at", "created_at"]
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.read_at is not None


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Ce qu'une application envoie pour se faire prévenir.

    `token` est déclaré à la main, sans le validateur d'unicité que DRF
    ajoute d'office sur un champ `unique`. Celui-ci refusait en 400 tout
    réenregistrement : relancer l'application échouait, et surtout un
    second compte sur le même téléphone ne pouvait plus reprendre
    l'appareil, si bien que les notifications continuaient de partir
    vers le compte précédent. La vue fait un `update_or_create`, qui est
    exactement la réponse juste à un jeton déjà connu.
    """

    token = serializers.CharField(max_length=255)

    class Meta:
        model = DeviceToken
        fields = ["token", "platform"]
