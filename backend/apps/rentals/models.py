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
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rental_requests",
        verbose_name=_("client"),
    )
    start_date = models.DateField(_("du"))
    end_date = models.DateField(_("au"))
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
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="rental_request_dates_ordered",
            ),
        ]

    def __str__(self):
        return f"{self.product_id} · {self.start_date} → {self.end_date}"

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("La date de fin ne peut pas précéder la date de début.")}
            )

    @property
    def contact_released(self):
        return self.contact_released_at is not None

    @property
    def nights(self):
        """Durée en jours, bornes comprises — ce qu'un loueur appelle la durée."""
        return (self.end_date - self.start_date).days + 1
