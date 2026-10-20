"""Ce qu'un adaptateur doit rendre, et rien de plus.

Un adaptateur sait parler à **une** source et produit des `RawListing`. Il
ne connaît ni les modèles Django, ni la déduplication, ni la modération :
c'est ce qui permet d'en ajouter, d'en retirer ou d'en remplacer un sans
toucher au reste.

Un champ qu'une source ne fournit pas reste `None`. Un adaptateur ne devine
jamais : deviner ici, c'est fabriquer une donnée fausse que plus personne ne
saura distinguer d'une donnée vérifiée.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawListing:
    """Une annonce telle que la source la présente, avant interprétation."""

    external_id: str | None = None
    original_url: str | None = None
    title: str | None = None
    description: str | None = None
    price_text: str | None = None
    currency: str | None = None
    price_period: str | None = None
    listing_type: str | None = None
    category_hint: str | None = None
    city: str | None = None
    area: str | None = None
    region: str | None = None
    country: str | None = None
    image_urls: list[str] = field(default_factory=list)
    contact_public: str | None = None
    collected_at: datetime | None = None
    raw: dict = field(default_factory=dict)


class SourceAdapter(ABC):
    """Base commune. `fetch()` peut lever : l'appelant journalise et poursuit."""

    #: Identifiant écrit dans `ListingSource.config["adapter"]`.
    key: str = ""

    def __init__(self, source):
        self.source = source
        self.config = source.config or {}

    @abstractmethod
    def fetch(self):
        """Itère sur les `RawListing` de la source."""

    # -- utilitaires partagés ------------------------------------------

    def mapped(self, row, name, default=None):
        """Lit `row[colonne]` où la colonne est nommée dans la configuration.

        Permet d'accepter un CSV partenaire dont les en-têtes ne sont pas
        les nôtres, sans écrire un adaptateur par partenaire.
        """
        mapping = self.config.get("fields", {})
        key = mapping.get(name, name)
        value = row.get(key, default)
        if isinstance(value, str):
            value = value.strip()
        return value or default


class AdapterError(Exception):
    """La source n'a pas pu être lue ; le détail part dans le rapport."""


_REGISTRY = {}


def register(cls):
    _REGISTRY[cls.key] = cls
    return cls


def get_adapter(source):
    """Instancie l'adaptateur déclaré par la source."""
    from . import csv_file, feed, json_api  # noqa: F401  (enregistrement)

    key = (source.config or {}).get("adapter") or source.kind
    adapter = _REGISTRY.get(key)
    if adapter is None:
        raise AdapterError(
            f"Aucun adaptateur « {key} ». Disponibles : {', '.join(sorted(_REGISTRY)) or '(aucun)'}."
        )
    return adapter(source)
