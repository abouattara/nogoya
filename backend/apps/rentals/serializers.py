"""Ce que chacun voit d'une demande de location.

Deux sérialiseurs, parce que deux lecteurs : le client suit l'avancement de
sa demande, l'équipe la traite. Le client ne doit jamais voir la note
interne, ni savoir qui de l'équipe s'en occupe.
"""
from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Product
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.accounts.models import phone_validator
from apps.accounts.validators import normalize_phone
from apps.catalog.serializers import ProductListSerializer

from .models import RentalRequest


class RentalRequestCreateSerializer(serializers.ModelSerializer):
    """Ce qu'un client soumet."""

    # Declare a la main, sans le validateur du modele : celui-ci s'applique
    # AVANT `validate()`, si bien qu'un numero ecrit « 70 11 22 33 » — la
    # facon normale de l'ecrire — etait refuse pour ses espaces avant meme
    # d'avoir ete normalise. On normalise d'abord, on valide ensuite.
    guest_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = RentalRequest
        # `thread` est en lecture seule mais doit sortir : sans lui, le
        # client venait d'envoyer sa demande et n'avait aucun lien pour la
        # suivre — l'écran affichait « Toutes mes demandes » faute de mieux.
        fields = [
            "id", "product", "start_date", "end_date", "open_ended",
            "message", "guest_name", "guest_phone", "thread", "status",
        ]
        read_only_fields = ["thread", "status"]

    def validate_guest_phone(self, value):
        if not value:
            return ""
        phone = normalize_phone(value)
        try:
            phone_validator(phone)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return phone

    def validate_product(self, value):
        if value.status != Product.Status.APPROVED or not value.is_active:
            raise serializers.ValidationError("Ce bien n'est pas disponible à la demande.")
        if settings.LAUNCH_RENTAL_ONLY and value.listing_type != Product.ListingType.RENT:
            raise serializers.ValidationError("Seules les locations acceptent une demande.")
        return value

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if attrs.get("open_ended"):
            # « Je ne sais pas encore quand je rendrai le bien » : on efface
            # la date de fin plutôt que d'en inventer une.
            attrs["end_date"] = None
            end = None
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "La date de fin ne peut pas précéder la date de début."}
            )
        if not end and not attrs.get("open_ended"):
            raise serializers.ValidationError(
                {"end_date": "Indiquez une date de fin, ou cochez « durée indéterminée »."}
            )

        request = self.context.get("request")
        product = attrs.get("product")
        user = getattr(request, "user", None) if request else None

        if user is not None and user.is_authenticated:
            # Un compte connecté n'a pas à saisir ses coordonnées, et ne
            # doit pas pouvoir en inventer d'autres.
            attrs.pop("guest_name", None)
            attrs.pop("guest_phone", None)
            if product is not None:
                profile = getattr(user, "supplier_profile", None)
                if profile is not None and product.supplier_id == profile.pk:
                    raise serializers.ValidationError(
                        {"product": "Vous ne pouvez pas demander votre propre bien."}
                    )
        else:
            phone = attrs.get("guest_phone") or ""
            if not phone:
                raise serializers.ValidationError(
                    {"guest_phone": "Indiquez un numéro pour que nous puissions vous rappeler."}
                )
            attrs["guest_phone"] = phone

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
            "id", "product", "start_date", "end_date", "open_ended",
            "message", "status", "status_label", "contact_released", "nights",
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
            "requester_phone", "has_account",
            "supplier_checked_at", "contact_released_at", "staff_note",
        ]
        read_only_fields = [
            f for f in fields if f != "staff_note"
        ]

    requester_phone = serializers.CharField(read_only=True)
    has_account = serializers.SerializerMethodField()

    def get_has_account(self, obj):
        return obj.client_id is not None

    def get_client_name(self, obj):
        # Un visiteur sans compte a tout de même un nom à afficher.
        return obj.requester_label

    def get_supplier_name(self, obj):
        return obj.product.supplier.user.public_name("Fournisseur")

    def get_handled_by_name(self, obj):
        return obj.handled_by.public_name() if obj.handled_by_id else None
