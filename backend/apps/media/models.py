"""Media attached to a chat message.

One table for images, videos and voice notes instead of a column per kind
on `Message`: adding video that way would have meant `video_file`,
`video_duration`, `video_poster`, `video_width`… and a serializer that grows
a branch for each. Here a message simply has attachments.

Only metadata lives in PostgreSQL. The bytes live in the object store, under
`chat/{conversation}/{message}/…`, and the database keeps the key.
"""
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


def attachment_upload_to(instance, filename):
    """chat/{conversation}/{message}/{random}.{ext}

    The user's filename never reaches storage: it could carry `../`, a
    double extension or simply their name. We keep the extension only after
    checking it against the whitelist, and generate everything else.
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    extension = "".join(c for c in extension if c.isalnum())[:5] or "bin"
    message = instance.message
    return f"chat/{message.conversation_id}/{message.pk}/{uuid.uuid4().hex}.{extension}"


def poster_upload_to(instance, filename):
    message = instance.message
    return f"chat/{message.conversation_id}/{message.pk}/{uuid.uuid4().hex}-poster.jpg"


class MessageAttachment(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", _("Image")
        VIDEO = "video", _("Vidéo")
        AUDIO = "audio", _("Audio")

    class Status(models.TextChoices):
        # `UPLOADING` exists for the client's optimistic row; the server
        # never writes it. Kept so the states in the API match the ones the
        # interface shows.
        UPLOADING = "uploading", _("Envoi")
        PROCESSING = "processing", _("Traitement")
        READY = "ready", _("Prêt")
        FAILED = "failed", _("Échec")

    message = models.ForeignKey(
        "messaging.Message", on_delete=models.CASCADE, related_name="attachments"
    )
    kind = models.CharField(max_length=8, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)

    file = models.FileField(upload_to=attachment_upload_to)
    # Images get a smaller rendition, videos a still frame. Same column: in
    # both cases it is "the small image to show before loading the real one".
    poster = models.ImageField(upload_to=poster_upload_to, blank=True, null=True)

    mime_type = models.CharField(max_length=80, blank=True)
    size = models.PositiveBigIntegerField(default=0, help_text=_("Taille stockée, en octets."))
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    duration = models.PositiveIntegerField(default=0, help_text=_("Secondes, audio et vidéo."))
    position = models.PositiveSmallIntegerField(default=0)

    # SHA-256 of the *stored* bytes. Not used to deduplicate today — it is
    # what makes deduplication possible later without a re-scan, and it
    # identifies a file in logs without exposing its key.
    checksum = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["message", "position"])]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"

    def delete_files(self):
        """Remove the bytes from storage; the row goes with the message."""
        for field in (self.file, self.poster):
            if field:
                field.delete(save=False)
