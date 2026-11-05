from django.conf import settings
from django.db import models

from .terms import TERMS_VERSION


class TermsAcceptance(models.Model):
    """La trace qu'une personne a accepté les conditions, et lesquelles.

    Sans version, la trace ne vaut rien : six mois plus tard, personne ne
    saura quel texte avait été coché. On garde donc le numéro de version à
    côté de la date, et une ligne par version acceptée, de sorte qu'un
    changement de conditions se redemande sans effacer l'accord précédent.

    Rien d'autre n'est conservé. L'adresse IP aurait été une preuve de
    plus, mais c'est une donnée personnelle de plus à protéger pour un
    gain qui ne se présentera presque jamais.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="terms_acceptances",
        verbose_name="Compte",
    )
    version = models.CharField("Version acceptée", max_length=32)
    accepted_at = models.DateTimeField("Accepté le", auto_now_add=True)

    class Meta:
        verbose_name = "Acceptation des conditions"
        verbose_name_plural = "Acceptations des conditions"
        ordering = ["-accepted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "version"], name="unique_terms_acceptance_per_version"
            )
        ]

    def __str__(self):
        return f"{self.user} a accepté la version {self.version}"

    @classmethod
    def record(cls, user, version=TERMS_VERSION):
        """Inscrit l'acceptation, sans jamais la compter deux fois."""
        acceptance, _ = cls.objects.get_or_create(user=user, version=version)
        return acceptance

    @classmethod
    def is_up_to_date(cls, user):
        """Cette personne a-t-elle accepté les conditions en vigueur ?"""
        if not getattr(user, "is_authenticated", False):
            return False
        return cls.objects.filter(user=user, version=TERMS_VERSION).exists()
