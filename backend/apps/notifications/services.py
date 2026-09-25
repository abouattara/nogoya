"""Single entry point for creating notifications.

Every producer (messaging, moderation, live...) goes through `notify` so the
delivery side — currently a DB row polled by the frontend, later a WebSocket
push — can change in one place.
"""
import logging

from django.utils import timezone

from .models import Notification

logger = logging.getLogger("nogoya.notifications")


def notify(user, *, type, title, message="", url="", data=None):
    if user is None:
        return None
    notification = Notification.objects.create(
        user=user, type=type, title=title, message=message, url=url, data=data or {},
    )
    logger.info("Notification %s created for user %s", type, user.pk)
    return notification


def unread_count_for(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def mark_all_read(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
