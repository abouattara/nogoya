from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """Generic in-app notification.

    `data` carries whatever the frontend needs to route the click (a product
    slug, a conversation id...) so adding a new notification type never
    requires a migration — only a new `Type` value and a producer call.
    """

    class Type(models.TextChoices):
        NEW_MESSAGE = "new_message", _("Nouveau message")
        NEW_PRODUCT = "new_product", _("Nouvelle annonce")
        PRODUCT_UPDATED = "product_updated", _("Annonce mise à jour")
        PRODUCT_APPROVED = "product_approved", _("Annonce approuvée")
        PRODUCT_REJECTED = "product_rejected", _("Annonce rejetée")
        FAVORITE = "favorite", _("Favori")
        LIVE_STARTED = "live_started", _("Live démarré")
        SYSTEM = "system", _("Système")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(_("type"), max_length=32, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(_("titre"), max_length=200)
    message = models.TextField(_("message"), blank=True)
    url = models.CharField(
        _("lien"), max_length=255, blank=True,
        help_text=_("Chemin frontend ouvert au clic, ex : /compte/messages/12"),
    )
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.get_type_display()} → {self.user_id}"
