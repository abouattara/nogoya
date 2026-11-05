from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.legal.models import TermsAcceptance
from apps.legal.terms import TERMS_VERSION

from .validators import normalize_phone

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    """Safe-to-share subset, embedded in products / supplier catalogs."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "avatar", "role", "created_at"]

    def get_full_name(self, obj):
        return obj.public_name()


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "phone", "first_name", "last_name", "email", "gender",
            "birth_date", "avatar", "role", "is_phone_verified", "created_at",
            # Le frontend en a besoin pour proposer — ou non — l'écran de
            # modération. Ce n'est pas un contrôle d'accès : chaque appel
            # d'administration est revérifié côté serveur.
            "is_staff",
        ]
        read_only_fields = [
            "id", "phone", "role", "is_phone_verified", "created_at", "is_staff",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """Créer un compte, conditions acceptées.

    La case cochée dans le navigateur ne prouve rien : elle se décoche
    avec deux lignes de console, et l'appel part quand même. L'acceptation
    est donc une donnée du formulaire que le serveur exige, vérifie, et
    inscrit dans une ligne datée qui porte la version du texte affiché.
    """

    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True, label="Confirmation")
    accept_terms = serializers.BooleanField(write_only=True, label="Conditions acceptées")
    terms_version = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "phone", "first_name", "last_name", "email", "role",
            "password", "password2", "accept_terms", "terms_version",
        ]

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                "Vous devez accepter les conditions d'utilisation pour créer un compte."
            )
        return value

    def validate_terms_version(self, value):
        """Accepter, oui, mais le texte que le site affiche aujourd'hui.

        Un onglet resté ouvert pendant une mise à jour des conditions
        enverrait l'accord sur l'ancien texte. On le refuse avec une phrase
        qui dit quoi faire, plutôt que d'enregistrer un accord portant sur
        autre chose que ce qui s'applique.
        """
        if value and value != TERMS_VERSION:
            raise serializers.ValidationError(
                "Les conditions d'utilisation ont changé. Rechargez la page "
                "pour lire la version en vigueur, puis réessayez."
            )
        return value

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ce numéro est déjà associé à un compte.")
        return phone

    def validate_role(self, value):
        if value not in (User.Role.SUPPLIER, User.Role.VISITOR):
            raise serializers.ValidationError("Rôle invalide.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        probe = User(
            phone=attrs.get("phone", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
            email=attrs.get("email", ""),
        )
        try:
            validate_password(attrs["password"], probe)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("accept_terms")
        validated_data.pop("terms_version", None)
        user = User(**validated_data)
        user.set_password(password)
        # Le compte et sa trace d'acceptation naissent ensemble. Les
        # requêtes ne sont pas atomiques par défaut sur ce projet : sans
        # cette transaction, une panne entre les deux écritures laisserait
        # un compte dont plus personne ne peut dire ce qu'il a accepté.
        with transaction.atomic():
            user.save()
            TermsAcceptance.record(user)
        return user
