from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer

from .models import SupplierProfile


class SupplierPublicSerializer(serializers.ModelSerializer):
    """Public supplier catalog page.

    The phone number is only revealed to authenticated visitors — the
    "contact the supplier" action from the product page — never to
    anonymous crawlers/scrapers.
    """

    user = UserPublicSerializer(read_only=True)
    products_count = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = SupplierProfile
        fields = [
            "id", "user", "city", "bio", "is_verified", "rating_avg",
            "products_count", "phone", "whatsapp_number", "created_at",
        ]

    def get_products_count(self, obj):
        return obj.products.filter(status="approved").count()

    def get_phone(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user.phone
        return None

    def get_whatsapp_number(self, obj):
        # Opt-in, so unlike `phone` it may be shown to anonymous visitors too.
        if obj.allow_whatsapp_contact and obj.whatsapp_number:
            return obj.whatsapp_number
        return None


class SupplierMeSerializer(serializers.ModelSerializer):
    """Editable by the supplier for their own profile."""

    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = SupplierProfile
        fields = [
            "id", "user", "city", "address", "bio", "is_verified", "rating_avg",
            "whatsapp_number", "allow_whatsapp_contact",
        ]
        read_only_fields = ["id", "is_verified", "rating_avg"]
