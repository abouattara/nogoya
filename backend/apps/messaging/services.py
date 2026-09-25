from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message


def get_or_create_conversation(user_a, user_b, product=None):
    if user_a.pk == user_b.pk:
        raise ValueError("Un utilisateur ne peut pas démarrer une conversation avec lui-même.")
    low, high = sorted([user_a, user_b], key=lambda u: u.pk)
    conversation, created = Conversation.objects.get_or_create(
        participant_low=low, participant_high=high,
        defaults={"initial_product": product},
    )
    return conversation, created


def participant_filter(user):
    return Q(participant_low=user) | Q(participant_high=user)


def mark_read(conversation, reader):
    """Marks every message from the other participant as read by `reader`."""
    Message.objects.filter(
        conversation=conversation, read_at__isnull=True,
    ).exclude(sender=reader).update(read_at=timezone.now())


def unread_count_for(user):
    return Message.objects.filter(
        conversation__in=Conversation.objects.filter(participant_filter(user)),
        read_at__isnull=True,
    ).exclude(sender=user).count()
