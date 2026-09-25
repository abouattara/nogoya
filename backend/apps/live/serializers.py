from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.catalog.serializers import ProductListSerializer

from .models import LiveMessage, LiveProduct, LiveSession


class LiveProductSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = LiveProduct
        fields = ["id", "product", "position", "is_featured", "started_at", "ended_at"]


class LiveSessionSerializer(serializers.ModelSerializer):
    host = UserPublicSerializer(read_only=True)
    live_products = LiveProductSerializer(many=True, read_only=True)
    current_viewers = serializers.ReadOnlyField()

    class Meta:
        model = LiveSession
        fields = [
            "id", "host", "title", "description", "status", "thumbnail",
            "scheduled_for", "started_at", "ended_at", "peak_viewers",
            "current_viewers", "provider", "playback_url", "live_products",
            "created_at",
        ]
        read_only_fields = [
            "host", "status", "started_at", "ended_at", "peak_viewers",
            "current_viewers", "playback_url", "created_at",
        ]


class LiveSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = ["id", "title", "description", "thumbnail", "scheduled_for"]


class LiveMessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = LiveMessage
        fields = ["id", "sender", "message", "product", "created_at"]
        read_only_fields = ["sender", "created_at"]
