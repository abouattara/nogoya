import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager

phone_validator = RegexValidator(
    regex=r"^\+?\d{8,15}$",
    message=_("Numéro invalide. Utilisez 8 à 15 chiffres, éventuellement préfixés par +."),
)


def avatar_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"avatars/{uuid.uuid4().hex}.{ext}"


class User(AbstractUser):
    """Custom user authenticated by phone number.

    The built-in ``username`` field is removed; ``phone`` is the login identifier.
    ``first_name`` / ``last_name`` from AbstractUser are reused (no duplication).
    """

    class Role(models.TextChoices):
        SUPPLIER = "supplier", _("Fournisseur")
        VISITOR = "visitor", _("Visiteur")

    class Gender(models.TextChoices):
        MALE = "M", _("Homme")
        FEMALE = "F", _("Femme")
        OTHER = "X", _("Autre")

    # Remove username; authenticate on phone instead.
    username = None

    phone = models.CharField(
        _("téléphone"),
        max_length=20,
        unique=True,
        validators=[phone_validator],
    )
    role = models.CharField(
        _("rôle"), max_length=20, choices=Role.choices, default=Role.VISITOR
    )
    gender = models.CharField(
        _("genre"), max_length=1, choices=Gender.choices, blank=True
    )
    birth_date = models.DateField(_("date de naissance"), null=True, blank=True)
    avatar = models.ImageField(
        _("photo de profil"), upload_to=avatar_upload_to, null=True, blank=True
    )
    email = models.EmailField(_("adresse email"), blank=True)
    is_phone_verified = models.BooleanField(_("téléphone vérifié"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []  # phone + password only for createsuperuser

    objects = UserManager()

    class Meta:
        verbose_name = _("utilisateur")
        verbose_name_plural = _("utilisateurs")

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.phone})" if full else self.phone

    @property
    def is_supplier(self):
        return self.role == self.Role.SUPPLIER

    @property
    def is_visitor(self):
        return self.role == self.Role.VISITOR
