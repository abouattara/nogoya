"""La demande de location : ce qui déclenche notre travail.

Dans le schéma intermédié, un client ne contacte pas un fournisseur. Il nous
dit ce qu'il veut et pour quelles dates ; nous vérifions auprès du
fournisseur que le bien est réellement disponible ; et seulement ensuite
nous mettons les deux en relation.

Cette table est le registre de ce cheminement. Elle existe pour trois
raisons précises :

* **Les dates.** Sans elles, « est-ce disponible ? » n'a pas de réponse. Un
  logement libre en mars ne l'est pas en avril, et nous ne pouvons pas
  interroger le fournisseur sans savoir quand.
* **La preuve de la vérification.** `supplier_checked_at` dit que quelqu'un
  a réellement appelé le fournisseur. Sans cette trace, « disponible »
  n'est qu'une supposition qui engage NOGOYA.
* **La libération des coordonnées.** `contact_released_at` est la seule
  chose qui autorise un client à voir le numéro du fournisseur. C'est un
  geste explicite, daté, imputable — pas un effet de bord d'un changement
  de statut.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import phone_validator
from apps.core.models import TimeStampedModel


class RentalRequest(TimeStampedModel):
    """Un client veut louer un bien, à telles dates."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", _("Reçue")
        CHECKING = "checking", _("Vérification auprès du fournisseur")
        AVAILABLE = "available", _("Disponible")
        UNAVAILABLE = "unavailable", _("Indisponible")
        CONNECTED = "connected", _("Mise en relation faite")
        CANCELLED = "cancelled", _("Annulée")

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="rental_requests",
        verbose_name=_("bien demandé"),
    )
    # --- qui demande -------------------------------------------------
    # Le compte est facultatif. Exiger une inscription avant la premiere
    # question fait fuir une part des clients, et le schema intermedie ne
    # l'impose pas : c'est NOGOYA qui rappelle, et un numero suffit pour
    # cela. Un visiteur identifie garde l'avantage de suivre sa demande
    # dans son espace et d'echanger dans un fil.
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
        related_name="rental_requests", verbose_name=_("client"),
    )
    guest_name = models.CharField(_("nom du demandeur"), max_length=120, blank=True)
    guest_phone = models.CharField(
        _("téléphone du demandeur"), max_length=20, blank=True,
        validators=[phone_validator],
        help_text=_("Renseigné quand la demande vient d'un visiteur sans compte."),
    )

    # --- quand ---------------------------------------------------------
    start_date = models.DateField(_("à partir du"))
    end_date = models.DateField(
        _("jusqu'au"), null=True, blank=True,
        help_text=_("Vide lorsque la durée n'est pas connue — un logement, typiquement."),
    )
    open_ended = models.BooleanField(
        _("durée indéterminée"), default=False,
        help_text=_(
            "Le demandeur ne sait pas encore quand il rendra le bien. "
            "Demander une date de fin pour une maison n'avait pas de sens."
        ),
    )
    message = models.TextField(_("message"), blank=True)

    status = models.CharField(
        _("statut"), max_length=12, choices=Status.choices, default=Status.SUBMITTED,
        db_index=True,
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="handled_rental_requests", verbose_name=_("traitée par"),
    )
    supplier_checked_at = models.DateTimeField(
        _("fournisseur consulté le"), null=True, blank=True,
        help_text=_("Renseigné quand l'équipe a réellement vérifié la disponibilité."),
    )
    contact_released_at = models.DateTimeField(
        _("coordonnées transmises le"), null=True, blank=True,
        help_text=_(
            "Tant que ce champ est vide, le client ne voit pas les coordonnées "
            "du fournisseur — y compris en appelant l'API directement."
        ),
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="released_rental_requests", verbose_name=_("transmises par"),
    )
    staff_note = models.TextField(
        _("note interne"), blank=True,
        help_text=_("Jamais montrée au client ni au fournisseur."),
    )
    thread = models.ForeignKey(
        "messaging.Conversation", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="rental_requests", verbose_name=_("fil de discussion"),
    )

    class Meta:
        verbose_name = _("demande de location")
        verbose_name_plural = _("demandes de location")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["product", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                # Une date de fin absente est permise (durée indéterminée) ;
                # une date de fin anterieure au debut ne l'est jamais.
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="rental_request_dates_ordered",
            ),
            models.CheckConstraint(
                # Sans compte ni numero, personne ne peut etre rappele : la
                # demande serait une impasse pour tout le monde.
                condition=~models.Q(client__isnull=True, guest_phone=""),
                name="rental_request_has_a_way_to_reply",
            ),
        ]

    def __str__(self):
        return f"{self.product_id} · {self.start_date} → {self.end_date}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("La date de fin ne peut pas précéder la date de début.")}
            )
        if self.client_id is None and not self.guest_phone:
            raise ValidationError(
                {"guest_phone": _("Un numéro est nécessaire pour vous recontacter.")}
            )

    @property
    def contact_released(self):
        return self.contact_released_at is not None

    @property
    def nights(self):
        """Durée en jours, bornes comprises. `None` si elle est inconnue."""
        if self.end_date is None:
            return None
        return (self.end_date - self.start_date).days + 1

    @property
    def requester_label(self):
        """Comment nommer le demandeur, avec ou sans compte."""
        if self.client_id:
            return self.client.public_name("Client")
        return self.guest_name or "Visiteur"

    @property
    def requester_phone(self):
        """Par où le rappeler. C'est tout l'intérêt d'accepter les visiteurs."""
        return self.client.phone if self.client_id else self.guest_phone
