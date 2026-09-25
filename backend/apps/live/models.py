"""Live sessions — business models only.

No video infrastructure is bundled: `provider` / `provider_session_id` /
`playback_url` / `ingest_url` are the seams where LiveKit, Cloudflare Stream
or plain WebRTC plug in later without touching the rest of the schema.
See LIVE.md.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


def live_thumbnail_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"live/thumbnails/{uuid.uuid4().hex}.{ext}"


class LiveSession(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        SCHEDULED = "scheduled", _("Programmé")
        LIVE = "live", _("En direct")
        ENDED = "ended", _("Terminé")
        CANCELLED = "cancelled", _("Annulé")

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_sessions"
    )
    title = models.CharField(_("titre"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(
        _("statut"), max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    thumbnail = models.ImageField(upload_to=live_thumbnail_upload_to, null=True, blank=True)
    scheduled_for = models.DateTimeField(_("programmé pour"), null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    peak_viewers = models.PositiveIntegerField(default=0)

    # Streaming provider seams — empty until a provider is wired in.
    provider = models.CharField(_("fournisseur vidéo"), max_length=40, blank=True)
    provider_session_id = models.CharField(max_length=255, blank=True)
    playback_url = models.URLField(blank=True)
    ingest_url = models.URLField(blank=True)

    class Meta:
        verbose_name = _("session live")
        verbose_name_plural = _("sessions live")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "started_at"])]

    @property
    def is_open(self):
        return self.status == self.Status.LIVE

    @property
    def current_viewers(self):
        return self.viewers.filter(left_at__isnull=True).count()

    def start(self):
        self.status = self.Status.LIVE
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def end(self):
        self.status = self.Status.ENDED
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at", "updated_at"])
        self.viewers.filter(left_at__isnull=True).update(left_at=self.ended_at)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class LiveViewer(models.Model):
    """One presence record per (live, viewer) join."""

    live = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="viewers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="live_views",
    )
    visitor_id = models.CharField(max_length=32, blank=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-joined_at"]
        indexes = [models.Index(fields=["live", "left_at"])]

    def __str__(self):
        return f"Viewer {self.user_id or self.visitor_id} @ live {self.live_id}"


class LiveMessage(models.Model):
    live = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_messages"
    )
    message = models.TextField(_("message"))
    # A live chat message may point at one of the products being shown.
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="live_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["live", "created_at"])]


class LiveProduct(models.Model):
    """A product presented during a live, optionally pinned on screen."""

    live = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="live_products")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="live_appearances"
    )
    position = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(_("mis en avant"), default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["live", "product"], name="unique_product_per_live"),
        ]

    def feature(self):
        """Pin this product; only one product is featured at a time."""
        now = timezone.now()
        LiveProduct.objects.filter(live=self.live, is_featured=True).exclude(pk=self.pk).update(
            is_featured=False, ended_at=now
        )
        self.is_featured = True
        self.started_at = self.started_at or now
        self.ended_at = None
        self.save(update_fields=["is_featured", "started_at", "ended_at"])

    def unfeature(self):
        self.is_featured = False
        self.ended_at = timezone.now()
        self.save(update_fields=["is_featured", "ended_at"])
