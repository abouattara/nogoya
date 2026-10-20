"""D'où viennent les annonces que NOGOYA n'a pas reçues de ses propres membres.

Deux tables seulement :

* `ListingSource` — une source autorisée, et les conditions de cette
  autorisation. Une source naît **désactivée** et ne peut être activée sans
  qu'un humain ait écrit noir sur blanc ce que la source permet. Ce n'est
  pas une formalité : importer une annonce, c'est recopier le travail de
  quelqu'un, et la seule question qui compte est « en avons-nous le droit ».
* `ListingImport` — une ligne par annonce rencontrée, qu'elle ait donné un
  produit ou non. C'est le journal : il dit ce qui a été vu, quand, ce qu'on
  en a fait, et pourquoi quand on n'en a rien fait.

Ce que ces tables ne font **pas** : stocker des coordonnées personnelles
glanées dans une annonce. Un numéro de téléphone publié par une agence sur
son propre site est une donnée professionnelle ; le numéro d'un particulier
sur un groupe Facebook ne l'est pas. Dans le doute, on ne garde rien et on
renvoie vers l'annonce d'origine.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class ListingSource(TimeStampedModel):
    """Une provenance d'annonces, et les conditions qui l'autorisent."""

    class Kind(models.TextChoices):
        FILE = "file", _("Fichier CSV fourni par un partenaire")
        FEED = "feed", _("Flux RSS / Atom")
        API = "api", _("API JSON autorisée")
        MANUAL = "manual", _("Soumission manuelle")

    class RunStatus(models.TextChoices):
        NEVER = "never", _("Jamais exécutée")
        OK = "ok", _("Terminée")
        PARTIAL = "partial", _("Terminée avec des erreurs")
        FAILED = "failed", _("Échec")

    name = models.CharField(_("nom"), max_length=120, unique=True)
    slug = models.SlugField(_("identifiant"), max_length=140, unique=True)
    kind = models.CharField(_("type"), max_length=8, choices=Kind.choices)

    reference_url = models.URLField(
        _("site de référence"), blank=True,
        help_text=_("Page d'accueil ou mentions légales de la source."),
    )
    endpoint = models.CharField(
        _("point d'accès"), max_length=500, blank=True,
        help_text=_("URL du flux ou de l'API, ou chemin du fichier déposé pour une source « fichier »."),
    )
    config = models.JSONField(
        _("configuration"), default=dict, blank=True,
        help_text=_(
            "Correspondance des champs et options de l'adaptateur. "
            "N'y placez jamais de clé d'API : utilisez « variable d'environnement »."
        ),
    )
    credential_env_var = models.CharField(
        _("variable d'environnement portant la clé"), max_length=100, blank=True,
        help_text=_(
            "Nom de la variable, pas sa valeur — par exemple PARTENAIRE_X_API_KEY. "
            "Le secret reste hors de la base et hors du dépôt."
        ),
    )

    # --- autorisation ------------------------------------------------------
    is_active = models.BooleanField(
        _("active"), default=False,
        help_text=_("Une source inactive n'est jamais interrogée, ni manuellement ni automatiquement."),
    )
    authorization_note = models.TextField(
        _("autorisation et restrictions"), blank=True,
        help_text=_(
            "Ce que la source autorise, et sur quelle base : conditions d'utilisation, "
            "contrat, courriel d'accord. Obligatoire pour activer la source."
        ),
    )
    authorization_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="confirmed_listing_sources", verbose_name=_("autorisation vérifiée par"),
    )
    authorization_confirmed_at = models.DateTimeField(
        _("autorisation vérifiée le"), null=True, blank=True
    )
    allows_image_reuse = models.BooleanField(
        _("réutilisation des photos autorisée"), default=False,
        help_text=_(
            "Décoché, aucune photo n'est copiée : l'annonce renvoie vers la source. "
            "Une photo est une œuvre, et son auteur n'est pas celui qui publie l'annonce."
        ),
    )
    allows_contact_details = models.BooleanField(
        _("coordonnées professionnelles publiables"), default=False,
        help_text=_("À ne cocher que pour des coordonnées d'agence publiées par la source elle-même."),
    )

    # --- politesse technique ----------------------------------------------
    request_delay_seconds = models.PositiveSmallIntegerField(
        _("délai entre deux requêtes (s)"), default=2,
        help_text=_("Respecté par les adaptateurs qui font plusieurs appels."),
    )
    min_interval_minutes = models.PositiveIntegerField(
        _("intervalle minimal entre deux exécutions (min)"), default=360,
        help_text=_("L'import automatique saute une source relancée trop tôt."),
    )
    max_items_per_run = models.PositiveIntegerField(
        _("maximum d'annonces par exécution"), default=100,
    )

    # --- dernière exécution ------------------------------------------------
    last_run_at = models.DateTimeField(_("dernière exécution"), null=True, blank=True)
    last_run_status = models.CharField(
        _("résultat de la dernière exécution"), max_length=8,
        choices=RunStatus.choices, default=RunStatus.NEVER,
    )
    last_run_report = models.JSONField(_("rapport"), default=dict, blank=True)

    class Meta:
        verbose_name = _("source d'annonces")
        verbose_name_plural = _("sources d'annonces")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        # La garde est ici, pas seulement dans l'admin : une source activée
        # par un script ou un shell doit se heurter à la même règle.
        if self.is_active and not self.authorization_note.strip():
            raise ValidationError(
                {"authorization_note": _(
                    "Décrivez l'autorisation avant d'activer la source : sur quelle base "
                    "a-t-on le droit d'importer ces annonces ?"
                )}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def credential(self):
        """La clé d'API, lue dans l'environnement — jamais dans la base."""
        if not self.credential_env_var:
            return None
        import os

        return os.environ.get(self.credential_env_var) or None


class ListingImport(TimeStampedModel):
    """Une annonce rencontrée chez une source, et ce qu'elle est devenue."""

    class Status(models.TextChoices):
        PENDING = "pending", _("À examiner")
        IMPORTED = "imported", _("Importée en brouillon")
        DUPLICATE = "duplicate", _("Doublon probable")
        INVALID = "invalid", _("Données insuffisantes")
        ERROR = "error", _("Erreur de traitement")
        EXPIRED = "expired", _("Disparue de la source")

    source = models.ForeignKey(
        ListingSource, on_delete=models.CASCADE, related_name="imports",
        verbose_name=_("source"),
    )
    external_id = models.CharField(_("identifiant chez la source"), max_length=255, blank=True)
    original_url = models.URLField(_("URL d'origine"), max_length=500, blank=True)

    fingerprint = models.CharField(
        _("empreinte"), max_length=64, db_index=True,
        help_text=_("Clé de déduplication : voir sourcing/fingerprints.py."),
    )
    normalized = models.JSONField(
        _("données normalisées"), default=dict, blank=True,
        help_text=_("Ce qui a été compris de l'annonce, avant création du produit."),
    )
    raw_payload = models.JSONField(
        _("données brutes"), default=dict, blank=True,
        help_text=_("Conservées pour diagnostic, purgées par `prune_import_payloads`."),
    )

    status = models.CharField(
        _("statut"), max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="imports", verbose_name=_("annonce créée"),
    )
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="duplicates", verbose_name=_("doublon de"),
    )

    collected_at = models.DateTimeField(_("collectée le"))
    last_checked_at = models.DateTimeField(_("dernière vérification"), null=True, blank=True)
    error_message = models.TextField(_("message d'erreur"), blank=True)

    class Meta:
        verbose_name = _("annonce importée")
        verbose_name_plural = _("annonces importées")
        ordering = ["-collected_at", "-id"]
        constraints = [
            # Revoir la même annonce chez la même source met la ligne à jour,
            # elle n'en crée pas une seconde.
            models.UniqueConstraint(
                fields=["source", "fingerprint"], name="unique_import_per_source_fingerprint"
            ),
        ]
        indexes = [
            models.Index(fields=["source", "status"]),
            models.Index(fields=["status", "collected_at"]),
        ]

    def __str__(self):
        return f"{self.source.name} · {self.normalized.get('title') or self.external_id or self.pk}"
