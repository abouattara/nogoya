from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class SupplierProfile(TimeStampedModel):
    """Extra profile carried by users whose role is 'supplier'."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supplier_profile",
    )
    city = models.CharField(_("ville"), max_length=120, blank=True)
    address = models.CharField(_("adresse"), max_length=255, blank=True)
    bio = models.TextField(_("présentation"), blank=True)
    is_verified = models.BooleanField(_("vérifié"), default=False)
    # Denormalised average rating, refreshed by the reviews phase.
    rating_avg = models.DecimalField(
        _("note moyenne"), max_digits=3, decimal_places=2, default=0
    )
    whatsapp_number = models.CharField(
        _("numéro WhatsApp"), max_length=20, blank=True,
        help_text=_("Optionnel. Requis pour activer le contact WhatsApp."),
    )
    allow_whatsapp_contact = models.BooleanField(
        _("autoriser le contact WhatsApp"), default=False,
    )

    class Meta:
        verbose_name = _("profil fournisseur")
        verbose_name_plural = _("profils fournisseurs")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.phone} — {self.city or '—'}"
