"""Turning an upload into a stored attachment.

The order matters and is the same for every kind:

    validate → transform → store → record

Validation happens before a single byte is written, so a refused file never
occupies the bucket. Transformation is where an 8 MB phone photo becomes a
300 KB image; it is skipped for audio and video, which the browser already
encoded (see `docs`/STORAGE.md for why we do not transcode video here).
"""
import hashlib
import logging

from django.conf import settings
from django.core.exceptions import ValidationError

from .models import MessageAttachment
from .processing import UnprocessableImage, render_image, render_thumbnail
from .validators import (
    validate_audio_upload,
    validate_duration,
    validate_image_upload,
    validate_video_upload,
)

logger = logging.getLogger("nogoya.media")


def _checksum(django_file):
    """SHA-256 of the stored bytes, read in chunks so a video never lands
    wholly in memory."""
    digest = hashlib.sha256()
    django_file.seek(0)
    for chunk in iter(lambda: django_file.read(1024 * 1024), b""):
        digest.update(chunk)
    django_file.seek(0)
    return digest.hexdigest()


def build_image_attachment(message, upload, position=0):
    validate_image_upload(upload)
    try:
        rendered = render_image(upload)
    except UnprocessableImage as exc:
        logger.warning("Unreadable image from user=%s: %s", message.sender_id, exc)
        raise ValidationError("Cette image n'a pas pu être traitée.")

    attachment = MessageAttachment(
        message=message,
        kind=MessageAttachment.Kind.IMAGE,
        status=MessageAttachment.Status.READY,
        mime_type="image/jpeg",
        # The display rendition is what gets stored, so its dimensions are
        # the ones the bubble must reserve space for.
        width=rendered["display_size"][0],
        height=rendered["display_size"][1],
        position=position,
    )
    # `display`, not `master`: a chat picture is looked at, not re-edited, so
    # storing a 1600px master for every message would double the bill for a
    # size nothing ever requests.
    attachment.file.save(f"{message.pk}-{position}.jpg", rendered["display"], save=False)
    attachment.poster.save(f"{message.pk}-{position}-poster.jpg", rendered["thumbnail"], save=False)
    attachment.size = attachment.file.size
    attachment.checksum = _checksum(attachment.file)
    attachment.save()
    return attachment


def build_video_attachment(message, upload, poster=None, duration=0, position=0):
    validate_video_upload(upload)
    seconds = validate_duration(duration, settings.MAX_VIDEO_DURATION_SECONDS, "vidéo")

    attachment = MessageAttachment(
        message=message,
        kind=MessageAttachment.Kind.VIDEO,
        status=MessageAttachment.Status.READY,
        mime_type=(upload.content_type or "video/mp4").split(";")[0],
        duration=seconds,
        position=position,
    )
    attachment.file.save(getattr(upload, "name", "video.mp4"), upload, save=False)
    attachment.size = attachment.file.size
    attachment.checksum = _checksum(attachment.file)

    # The poster is a still the browser grabbed from the video: it saves the
    # server from decoding video just to show a thumbnail, and saves the
    # reader from downloading megabytes to see what a message contains.
    if poster is not None:
        try:
            validate_image_upload(poster)
            thumbnail = render_thumbnail(poster)
            attachment.poster.save(f"{message.pk}-{position}-poster.jpg", thumbnail["thumbnail"], save=False)
            attachment.width = thumbnail["width"]
            attachment.height = thumbnail["height"]
        except (ValidationError, UnprocessableImage) as exc:
            # A missing poster costs a placeholder, not a failed message.
            logger.info("Discarded unusable video poster: %s", exc)

    attachment.save()
    return attachment


def build_audio_attachment(message, upload, duration=0, position=0):
    validate_audio_upload(upload)
    seconds = validate_duration(duration, settings.MAX_AUDIO_DURATION_SECONDS, "vocal")

    attachment = MessageAttachment(
        message=message,
        kind=MessageAttachment.Kind.AUDIO,
        status=MessageAttachment.Status.READY,
        mime_type=(upload.content_type or "audio/webm").split(";")[0],
        duration=seconds,
        position=position,
    )
    attachment.file.save(getattr(upload, "name", "audio.webm"), upload, save=False)
    attachment.size = attachment.file.size
    attachment.checksum = _checksum(attachment.file)
    attachment.save()
    return attachment


def build_attachments(message, *, images=(), videos=(), audios=(), posters=(), durations=()):
    """Attach everything sent with one message, in order.

    Raises `ValidationError` on the first unusable file: a half-attached
    message is worse than a refused one, and the caller runs this inside a
    transaction.
    """
    limit = settings.MAX_ATTACHMENTS_PER_MESSAGE
    total = len(images) + len(videos) + len(audios)
    if total > limit:
        raise ValidationError(f"Un message accepte au maximum {limit} fichiers.")

    created, position = [], 0
    for upload in images:
        created.append(build_image_attachment(message, upload, position))
        position += 1
    for index, upload in enumerate(videos):
        poster = posters[index] if index < len(posters) else None
        duration = durations[index] if index < len(durations) else 0
        created.append(build_video_attachment(message, upload, poster, duration, position))
        position += 1
    for index, upload in enumerate(audios):
        offset = len(videos) + index
        duration = durations[offset] if offset < len(durations) else 0
        created.append(build_audio_attachment(message, upload, duration, position))
        position += 1
    return created
