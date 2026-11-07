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


class DeviceToken(models.Model):
    """Un appareil à prévenir quand l'application est fermée.

    Le jeton vient de Firebase et désigne une installation, pas une
    personne : réinstaller l'application en donne un nouveau, et
    l'ancien meurt sans prévenir. On le remplace donc par son contenu
    (`token` unique) plutôt que par couple (personne, appareil), et on
    supprime ceux que Firebase rejette à l'envoi.

    Un même jeton peut changer de propriétaire : deux comptes sur le
    même téléphone. C'est pourquoi `token` est unique tout court, et que
    l'enregistrement réaffecte la ligne au lieu d'en créer une seconde,
    qui enverrait les messages de l'un aux notifications de l'autre.
    """

    class Platform(models.TextChoices):
        ANDROID = "android", _("Android")
        IOS = "ios", _("iOS")
        WEB = "web", _("Web")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
        verbose_name=_("compte"),
    )
    token = models.CharField(_("jeton Firebase"), max_length=255, unique=True)
    platform = models.CharField(
        _("plateforme"), max_length=16, choices=Platform.choices, default=Platform.ANDROID
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("appareil")
        verbose_name_plural = _("appareils")
        ordering = ["-last_seen_at"]
        indexes = [models.Index(fields=["user"])]

    def __str__(self):
        return f"{self.get_platform_display()} de {self.user_id}"
