"""Product image handling, on top of the shared media pipeline."""
import logging

from apps.media.processing import UnprocessableImage, render_image

logger = logging.getLogger("nogoya.catalog")


def compress_product_image(product_image, *, save=True):
    """Store a display rendition plus an optimised master.

    `master` used to hold the untouched upload — up to 12 MB of phone photo,
    kept forever so a crop could be redone. A 1600px master is still far more
    resolution than any crop needs, and costs a fraction of the storage; the
    difference is invisible in the editor and very visible on the bill.

    Safe to call from a Celery task or synchronously; it never raises.
    """
    field = product_image.image
    if not field:
        return product_image
    try:
        rendered = render_image(field)
    except UnprocessableImage as exc:
        logger.warning("Cannot process image for ProductImage=%s: %s", product_image.pk, exc)
        return product_image

    name = field.name.rsplit("/", 1)[-1]
    product_image.width = rendered["width"]
    product_image.height = rendered["height"]
    # Keep the storage-assigned name; only the bytes change.
    product_image.image.save(name, rendered["display"], save=False)

    fields = ["image", "width", "height"]
    if not product_image.master:
        # Written once, from the first upload. Re-running this after a crop
        # must not turn the cropped version into the master, or the next edit
        # would start from an already-cropped file.
        product_image.master.save(f"master-{name}", rendered["master"], save=False)
        fields.append("master")

    if save:
        product_image.save(update_fields=fields)
    return product_image
