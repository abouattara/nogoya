
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    """Un fil entre un membre et l'équipe NOGOYA, à propos d'une annonce.

    **Le schéma a changé au lancement « location ».** Avant, un visiteur
    parlait directement au fournisseur. Désormais NOGOYA est au centre : un
    fournisseur échange avec l'équipe pour compléter ses annonces, un client
    échange avec l'équipe à propos d'un bien, et les deux ne se parlent
    jamais directement. C'est ce qui permet de vérifier une disponibilité
    avant de mettre en relation, et de ne pas livrer un numéro de téléphone
    sans l'avoir décidé.

    La paire ordonnée est conservée — l'un des deux côtés est le compte de
    service « NOGOYA » — parce que tout ce qui lit `has_participant`, les
    non-lus et les blocages continue de fonctionner. Ce que l'équipe écrit
    part au nom de NOGOYA ; `Message.staff_author` garde en interne quel
    membre de l'équipe a répondu.
    """

    class Audience(models.TextChoices):
        CLIENT = "client", _("Client")
        SUPPLIER = "supplier", _("Fournisseur")

    participant_low = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    participant_high = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    initial_product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="opened_conversations",
        help_text=_("Le produit à l'origine de la conversation (contexte affiché dans la liste)."),
    )

    audience = models.CharField(
        _("interlocuteur"), max_length=10, choices=Audience.choices, default=Audience.CLIENT,
        db_index=True,
        help_text=_("Ce que le membre est pour NOGOYA dans ce fil : un client ou un fournisseur."),
    )

    class Meta:
        constraints = [
            # Un fil par annonce, et un fil général sans annonce. Les deux
            # contraintes sont nécessaires : une contrainte unique traite
            # deux NULL comme distincts, donc la première seule laisserait
            # créer autant de fils généraux qu'on veut.
            models.UniqueConstraint(
                fields=["participant_low", "participant_high", "initial_product"],
                condition=models.Q(initial_product__isnull=False),
                name="unique_thread_per_pair_and_product",
            ),
            models.UniqueConstraint(
                fields=["participant_low", "participant_high"],
                condition=models.Q(initial_product__isnull=True),
                name="unique_general_thread_per_pair",
            ),
        ]
        ordering = ["-updated_at"]

    def other_participant(self, user):
        return self.participant_high if user_id_of(user) == self.participant_low_id else self.participant_low

    def has_participant(self, user):
        uid = user_id_of(user)
        return uid in (self.participant_low_id, self.participant_high_id)

    def __str__(self):
        return f"Conversation #{self.pk}"


def user_id_of(user):
    return user.pk


class ConversationBlock(models.Model):
    """One participant has blocked the other in this specific conversation."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="blocks")
    blocked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "blocked_by"], name="unique_block_per_conversation"),
        ]


def message_audio_upload_to(instance, filename):
    """Kept only because migration 0002 names it.

    Voice notes moved to `media.MessageAttachment`; the column it fed no
    longer exists. Deleting the function would make the historical migration
    unimportable, which is how a migration history stops replaying.
    """
    return f"messages/audio/{filename}"


class Message(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", _("Texte")
        AUDIO = "audio", _("Audio")
        IMAGE = "image", _("Image")
        VIDEO = "video", _("Vidéo")
        PRODUCT = "product", _("Annonce")
        SYSTEM = "system", _("Système")

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    message_type = models.CharField(
        _("type"), max_length=12, choices=Type.choices, default=Type.TEXT
    )
    body = models.TextField(_("message"), blank=True)
    shared_product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="shared_in_messages",
    )
    staff_author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="authored_support_messages", verbose_name=_("rédigé par"),
        help_text=_(
            "Le membre de l'équipe qui a réellement écrit ce message. "
            "Interne : le destinataire voit « NOGOYA »."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def save(self, *args, **kwargs):
        # Attachments are created after the message exists, so the type is
        # settled by `sync_type()` once they are in place. Here we only cover
        # the cases knowable from the message's own columns.
        if self.message_type not in (self.Type.SYSTEM,) and not self.pk:
            if self.shared_product_id and not self.body:
                self.message_type = self.Type.PRODUCT
            else:
                self.message_type = self.Type.TEXT
        super().save(*args, **kwargs)

    def sync_type(self):
        """Name the message after what it carries, media first.

        A photo with a caption reads as a photo in the conversation list,
        which is what someone scanning their messages expects.
        """
        if self.message_type == self.Type.SYSTEM:
            return self.message_type
        kinds = {a.kind for a in self.attachments.all()}
        if "video" in kinds:
            message_type = self.Type.VIDEO
        elif "image" in kinds:
            message_type = self.Type.IMAGE
        elif "audio" in kinds:
            message_type = self.Type.AUDIO
        elif self.shared_product_id and not self.body:
            message_type = self.Type.PRODUCT
        else:
            message_type = self.Type.TEXT
        if message_type != self.message_type:
            self.message_type = message_type
            super().save(update_fields=["message_type"])
        return message_type

    def __str__(self):
        return f"Message #{self.pk} ({self.conversation_id})"


class MessageReport(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
