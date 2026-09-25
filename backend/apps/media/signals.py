"""Storage follows the database.

Deleting a row does not delete a file: Django leaves the bytes behind. On a
chat that carries photos and videos, that means paying every month for media
nobody can reach any more. These receivers close the gap for the ordinary
path (a message, a conversation or an account being deleted); the
`prune_media` command handles what slips through — a crash between the
upload and the commit, mostly.
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import MessageAttachment

logger = logging.getLogger("nogoya.media")


@receiver(post_delete, sender=MessageAttachment)
def delete_attachment_files(sender, instance, **kwargs):
    """Remove the stored bytes once the row is gone.

    Runs after the delete has committed, and never raises: a storage hiccup
    must not turn "the message is deleted" into a 500. Anything left over is
    picked up by `prune_media`.
    """
    try:
        instance.delete_files()
    except Exception as exc:  # noqa: BLE001 - storage backends raise anything
        logger.warning("Could not delete files of attachment %s: %s", instance.pk, exc)
