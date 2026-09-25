"""What we accept as an upload, and why we never believe the browser.

The `Content-Type` a browser sends is a hint an attacker controls for free,
and so is the filename. Every check here ends at the bytes themselves: a
`.webm` that is really an HTML page is rejected whatever its headers claim.

Limits live in settings so an operator can tighten them without a deploy.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image as PILImage
from PIL import UnidentifiedImageError

# --- images ---------------------------------------------------------------

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif", "image/heic", "image/heif"}
IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF", "MPO", "HEIF"}

# --- video ----------------------------------------------------------------

VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}

# --- audio ----------------------------------------------------------------

AUDIO_CONTENT_TYPES = {
    "audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/aac", "audio/x-m4a",
}
AUDIO_EXTENSIONS = {"webm", "ogg", "oga", "mp3", "m4a", "mp4", "aac"}

# Container signatures. MediaRecorder produces WebM/Opus on Chrome, Firefox
# and Edge, and MP4/AAC on Safari; phones hand us MP4/MOV video.
_SIGNATURES = (
    (b"\x1a\x45\xdf\xa3", "webm"),   # EBML (WebM / Matroska)
    (b"OggS", "ogg"),
    (b"ID3", "mp3"),
    (b"\xff\xfb", "mp3"),
    (b"\xff\xf1", "aac"),
)


def _megabytes(value):
    return value // (1024 * 1024)


def _check_size(uploaded_file, limit, label):
    if uploaded_file.size == 0:
        raise ValidationError(f"Le fichier {label} est vide.")
    if uploaded_file.size > limit:
        raise ValidationError(f"Le fichier {label} dépasse {_megabytes(limit)} Mo.")


def _extension(uploaded_file):
    name = getattr(uploaded_file, "name", "") or ""
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _detect_container(head):
    for signature, name in _SIGNATURES:
        if head.startswith(signature):
            return name
    # ISO base media (MP4 / M4A / MOV): "ftyp" box at offset 4
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "mp4"
    return None


def validate_image_upload(uploaded_file):
    """Size, declared type, and a real decode by Pillow."""
    _check_size(uploaded_file, settings.MAX_IMAGE_UPLOAD_BYTES, "image")

    content_type = (uploaded_file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in IMAGE_CONTENT_TYPES:
        raise ValidationError(f"Format d'image non supporté : {content_type}.")

    try:
        uploaded_file.seek(0)
        with PILImage.open(uploaded_file) as img:
            img.verify()  # decodes headers, raises on a non-image payload
            detected = img.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("Ce fichier n'est pas une image valide.")
    finally:
        uploaded_file.seek(0)

    if detected not in IMAGE_FORMATS:
        raise ValidationError(f"Format d'image non supporté : {detected}.")
    return True


def validate_video_upload(uploaded_file):
    _check_size(uploaded_file, settings.MAX_VIDEO_UPLOAD_BYTES, "vidéo")

    content_type = (uploaded_file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in VIDEO_CONTENT_TYPES:
        raise ValidationError(f"Format vidéo non supporté : {content_type}.")

    extension = _extension(uploaded_file)
    if extension and extension not in VIDEO_EXTENSIONS:
        raise ValidationError(f"Extension vidéo non supportée : .{extension}")

    uploaded_file.seek(0)
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    if _detect_container(head) not in {"mp4", "webm"}:
        raise ValidationError("Ce fichier n'est pas une vidéo valide.")
    return True


def validate_audio_upload(uploaded_file):
    _check_size(uploaded_file, settings.MAX_AUDIO_UPLOAD_BYTES, "audio")

    content_type = (uploaded_file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in AUDIO_CONTENT_TYPES:
        raise ValidationError(f"Type audio non supporté : {content_type}.")

    extension = _extension(uploaded_file)
    if extension and extension not in AUDIO_EXTENSIONS:
        raise ValidationError(f"Extension audio non supportée : .{extension}")

    uploaded_file.seek(0)
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    if _detect_container(head) is None:
        raise ValidationError("Ce fichier n'est pas un enregistrement audio valide.")
    return True


def validate_duration(duration, limit, label):
    """Durations come from the browser, so they are a hint, not a fact.

    They are used for the player's progress bar and to refuse obviously
    oversized media early; the size limit is what actually protects storage.
    """
    try:
        seconds = int(float(duration))
    except (TypeError, ValueError):
        raise ValidationError(f"Durée {label} invalide.")
    if seconds <= 0:
        raise ValidationError(f"Durée {label} invalide.")
    if seconds > limit:
        raise ValidationError(f"Le {label} dépasse la durée maximale ({limit}s).")
    return seconds
