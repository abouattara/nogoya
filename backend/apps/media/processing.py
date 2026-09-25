"""One image pipeline for the whole project.

Product photos and chat images went through two different code paths doing
roughly the same thing; this is the single one. It takes whatever the user
sent and produces a sensible master plus the variants a page actually
displays — never a 20 MB original sitting in a bucket forever.

Design notes:

* **EXIF is applied, then dropped.** Phone photos carry an orientation flag
  (a picture that looks upright in the gallery but lands sideways in the
  browser) and often GPS coordinates. We rotate the pixels, then re-encode
  without any metadata, so sharing a photo never shares where it was taken.
* **Two variants, not ten.** A thumbnail for grids and bubbles, a display
  size for the full view. Every extra size costs storage on every upload for
  a resolution nothing requests.
* **JPEG, not WebP/AVIF.** Pillow writes all three, but WebP saves ~25 % on a
  format that every browser, every crawler and every WhatsApp share already
  handles. When image bandwidth becomes a real cost, `IMAGE_FORMAT` is the
  single place to change. Documented in STORAGE.md.
"""
import io
import logging

from django.core.files.base import ContentFile
from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError

logger = logging.getLogger("nogoya.media")

# (width, height) bounding boxes — images keep their aspect ratio.
MASTER_SIZE = (1600, 1600)
DISPLAY_SIZE = (900, 900)
THUMBNAIL_SIZE = (320, 320)

MASTER_QUALITY = 80
DISPLAY_QUALITY = 78
THUMBNAIL_QUALITY = 70

IMAGE_FORMAT = "JPEG"
IMAGE_EXTENSION = "jpg"


class UnprocessableImage(Exception):
    """The bytes are not an image we can read."""


def _open(file_or_bytes):
    try:
        if hasattr(file_or_bytes, "open"):
            file_or_bytes.open("rb")
        image = PILImage.open(file_or_bytes)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnprocessableImage(str(exc)) from exc
    # Applies the EXIF orientation flag to the pixels and returns a copy
    # without it, so the image can no longer be rotated twice.
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "P", "LA"):
        image = image.convert("RGB")
    return image


def _encode(image, box, quality):
    resized = image.copy()
    resized.thumbnail(box, PILImage.LANCZOS)
    buffer = io.BytesIO()
    # `save` on a fresh image drops EXIF, ICC and every other chunk.
    resized.save(buffer, format=IMAGE_FORMAT, quality=quality, optimize=True, progressive=True)
    return ContentFile(buffer.getvalue()), resized.size


def render_image(file_or_bytes):
    """Return the master, display and thumbnail renditions of one image.

    Raises `UnprocessableImage` when the bytes are not a readable image.
    """
    image = _open(file_or_bytes)
    master, master_size = _encode(image, MASTER_SIZE, MASTER_QUALITY)
    display, display_size = _encode(image, DISPLAY_SIZE, DISPLAY_QUALITY)
    thumbnail, thumbnail_size = _encode(image, THUMBNAIL_SIZE, THUMBNAIL_QUALITY)
    # Sizes are per rendition: callers store one of them, and the dimensions
    # they record must describe the file they actually stored — otherwise the
    # interface reserves the wrong space and every image jumps on load.
    return {
        "master": master,
        "display": display,
        "thumbnail": thumbnail,
        "master_size": master_size,
        "display_size": display_size,
        "thumbnail_size": thumbnail_size,
        "width": master_size[0],
        "height": master_size[1],
    }


def render_thumbnail(file_or_bytes):
    """Just the thumbnail — for posters, which need no other size."""
    image = _open(file_or_bytes)
    thumbnail, (width, height) = _encode(image, THUMBNAIL_SIZE, THUMBNAIL_QUALITY)
    return {"thumbnail": thumbnail, "width": width, "height": height}
