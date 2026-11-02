"""Ouvrir et lire les fils de discussion, dans le schéma intermédié.

Depuis le lancement « location », personne ne parle directement à personne :
chaque fil relie **un membre et l'équipe NOGOYA**. Un fournisseur y complète
ses annonces avec nous, un client y pose ses questions sur un bien. Les deux
ne se croisent jamais, ce qui est précisément ce qui nous permet de vérifier
une disponibilité avant d'annoncer quoi que ce soit, et de ne livrer un
numéro de téléphone que lorsque nous l'avons décidé.

Le compte de service porte ce rôle côté NOGOYA. Ce n'est pas une fausse
identité : il s'appelle NOGOYA, ne peut pas se connecter, et le message
qu'une personne de l'équipe écrit garde en interne son auteur réel
(`Message.staff_author`).
"""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message

SUPPORT_PHONE = "+22600000001"
SUPPORT_NAME = "NOGOYA"


def support_account():
    """Le compte au nom duquel l'équipe répond.

    Inactif et sans mot de passe utilisable : il existe pour porter un côté
    du fil, jamais pour qu'on s'y connecte.
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        phone=SUPPORT_PHONE,
        defaults={"first_name": SUPPORT_NAME, "last_name": "", "role": User.Role.VISITOR,
                  "is_active": False},
    )
    if created:
        user.set_unusable_password()
        user.is_active = False
        user.save(update_fields=["password", "is_active"])
    return user


def get_or_create_support_thread(member, *, product=None, audience=None):
    """Le fil entre ce membre et NOGOYA, à propos de ce bien.

    Un fil par annonce, plus un fil général sans annonce : un client qui
    pose des questions sur trois logements ne doit pas les mélanger, et
    l'équipe doit voir de quoi on parle sans remonter l'historique.
    """
    support = support_account()
    if member.pk == support.pk:
        raise ValueError("Le compte de service ne peut pas ouvrir un fil avec lui-même.")

    if audience is None:
        audience = (
            Conversation.Audience.SUPPLIER
            if getattr(member, "is_supplier", False)
            else Conversation.Audience.CLIENT
        )

    low, high = sorted([member, support], key=lambda u: u.pk)
    conversation, created = Conversation.objects.get_or_create(
        participant_low=low,
        participant_high=high,
        initial_product=product,
        defaults={"audience": audience},
    )
    return conversation, created


def member_of(conversation):
    """Le côté humain du fil — l'autre étant le compte de service."""
    support = support_account()
    if conversation.participant_low_id == support.pk:
        return conversation.participant_high
    return conversation.participant_low


def participant_filter(user):
    return Q(participant_low=user) | Q(participant_high=user)


def mark_read(conversation, reader):
    """Marque lus les messages que `reader` n'a pas écrits.

    Pour l'équipe, « lu » vaut pour tout le monde : un fil traité par une
    personne ne doit pas réapparaître non lu chez sa collègue.
    """
    queryset = Message.objects.filter(conversation=conversation, read_at__isnull=True)
    if getattr(reader, "is_staff", False):
        queryset = queryset.filter(staff_author__isnull=True)
    else:
        queryset = queryset.exclude(sender=reader)
    queryset.update(read_at=timezone.now())


def unread_count_for(user):
    if getattr(user, "is_staff", False):
        # L'équipe compte ce que les membres ont écrit et que personne n'a
        # encore traité, tous fils confondus.
        return Message.objects.filter(
            read_at__isnull=True, staff_author__isnull=True
        ).exclude(sender=support_account()).count()
    return Message.objects.filter(
        conversation__in=Conversation.objects.filter(participant_filter(user)),
        read_at__isnull=True,
    ).exclude(sender=user).count()
