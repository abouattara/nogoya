"""Ce que chacun voit d'une demande de location.

Deux sérialiseurs, parce que deux lecteurs : le client suit l'avancement de
sa demande, l'équipe la traite. Le client ne doit jamais voir la note
interne, ni savoir qui de l'équipe s'en occupe.
"""
from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Product
from apps.catalog.serializers import ProductListSerializer

from .models import RentalRequest


class RentalRequestCreateSerializer(serializers.ModelSerializer):
    """Ce qu'un client soumet."""

    class Meta:
        model = RentalRequest
        # `thread` est en lecture seule mais doit sortir : sans lui, le
        # client venait d'envoyer sa demande et n'avait aucun lien pour la
        # suivre — l'écran affichait « Toutes mes demandes » faute de mieux.
        fields = ["id", "product", "start_date", "end_date", "message", "thread", "status"]
        read_only_fields = ["thread", "status"]

    def validate_product(self, value):
        if value.status != Product.Status.APPROVED or not value.is_active:
            raise serializers.ValidationError("Ce bien n'est pas disponible à la demande.")
        if settings.LAUNCH_RENTAL_ONLY and value.listing_type != Product.ListingType.RENT:
            raise serializers.ValidationError("Seules les locations acceptent une demande.")
        return value

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "La date de fin ne peut pas précéder la date de début."}
            )
        request = self.context.get("request")
        product = attrs.get("product")
        if request and product:
            profile = getattr(request.user, "supplier_profile", None)
            if profile is not None and product.supplier_id == profile.pk:
                raise serializers.ValidationError(
                    {"product": "Vous ne pouvez pas demander votre propre bien."}
                )
        return attrs


class RentalRequestSerializer(serializers.ModelSerializer):
    """Ce que le client lit : l'avancement, et rien d'interne."""

    product = ProductListSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    contact_released = serializers.BooleanField(read_only=True)
    nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = RentalRequest
        fields = [
            "id", "product", "start_date", "end_date", "message",
            "status", "status_label", "contact_released", "nights",
            "thread", "created_at",
        ]
        read_only_fields = fields


class StaffRentalRequestSerializer(RentalRequestSerializer):
    """Ce que l'équipe lit : tout, y compris qui a fait quoi et quand."""

    client_name = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    handled_by_name = serializers.SerializerMethodField()

    class Meta(RentalRequestSerializer.Meta):
        fields = RentalRequestSerializer.Meta.fields + [
            "client_name", "supplier_name", "handled_by_name",
            "supplier_checked_at", "contact_released_at", "staff_note",
        ]
        read_only_fields = [
            f for f in fields if f != "staff_note"
        ]

    def get_client_name(self, obj):
        return obj.client.public_name("Client")

    def get_supplier_name(self, obj):
        return obj.product.supplier.user.public_name("Fournisseur")

    def get_handled_by_name(self, obj):
        return obj.handled_by.public_name() if obj.handled_by_id else None
