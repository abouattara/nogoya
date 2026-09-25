from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .validators import normalize_phone

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    """Safe-to-share subset, embedded in products / supplier catalogs."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "avatar", "role", "created_at"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "phone", "first_name", "last_name", "email", "gender",
            "birth_date", "avatar", "role", "is_phone_verified", "created_at",
        ]
        read_only_fields = ["id", "phone", "role", "is_phone_verified", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True, label="Confirmation")

    class Meta:
        model = User
        fields = [
            "phone", "first_name", "last_name", "email", "role",
            "password", "password2",
        ]

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
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
