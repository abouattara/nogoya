import logging

from celery import shared_task

logger = logging.getLogger("nogoya.catalog")


@shared_task
def compress_product_image_task(product_image_id):
    """Async wrapper around the compression service.

    Runs eagerly in dev (CELERY_TASK_ALWAYS_EAGER) and on a worker in prod.
    """
    from .models import ProductImage
    from .services import compress_product_image

    try:
        image = ProductImage.objects.get(pk=product_image_id)
    except ProductImage.DoesNotExist:
        logger.warning("ProductImage %s vanished before compression", product_image_id)
        return
    compress_product_image(image)
