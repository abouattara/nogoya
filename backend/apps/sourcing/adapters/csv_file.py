"""Un export CSV déposé par un partenaire.

C'est la source la plus utile au démarrage, et la seule qui ne dépende de
personne : une agence immobilière de Ouagadougou exporte son parc, on le
dépose sur le serveur, on importe. Pas de clé d'API à négocier, pas de
conditions d'utilisation à interpréter — l'accord est explicite puisque le
partenaire a fourni le fichier lui-même.

Les colonnes sont libres : `config["fields"]` fait la correspondance avec
nos noms. Exemple de configuration :

    {
      "adapter": "file",
      "delimiter": ";",
      "fields": {"title": "Libelle", "price_text": "Loyer", "city": "Ville"}
    }
"""
import csv
import io
from datetime import timezone as dt_timezone
from datetime import datetime
from pathlib import Path

from django.conf import settings

from .base import AdapterError, RawListing, SourceAdapter, register


@register
class CsvFileAdapter(SourceAdapter):
    key = "file"

    def fetch(self):
        path = self._resolve_path()
        collected = datetime.now(dt_timezone.utc)

        try:
            text = path.read_text(encoding=self.config.get("encoding", "utf-8-sig"))
        except OSError as exc:
            raise AdapterError(f"Fichier illisible : {exc}") from exc

        reader = csv.DictReader(io.StringIO(text), delimiter=self.config.get("delimiter", ","))
        if not reader.fieldnames:
            raise AdapterError("Fichier vide ou sans ligne d'en-tête.")

        for row in reader:
            images = self.mapped(row, "image_urls", "") or ""
            yield RawListing(
                external_id=self.mapped(row, "external_id"),
                original_url=self.mapped(row, "original_url"),
                title=self.mapped(row, "title"),
                description=self.mapped(row, "description"),
                price_text=self.mapped(row, "price_text"),
                currency=self.mapped(row, "currency"),
                price_period=self.mapped(row, "price_period"),
                listing_type=self.mapped(row, "listing_type"),
                category_hint=self.mapped(row, "category"),
                city=self.mapped(row, "city"),
                area=self.mapped(row, "area"),
                region=self.mapped(row, "region"),
                country=self.mapped(row, "country"),
                image_urls=[u.strip() for u in str(images).split("|") if u.strip()],
                contact_public=self.mapped(row, "contact_public"),
                collected_at=collected,
                raw=dict(row),
            )

    def _resolve_path(self):
        """Le fichier doit rester dans le dossier prévu pour les imports.

        `endpoint` vient de l'admin ; sans cette contrainte, « ../../.env »
        serait une adresse valable. On résout, puis on vérifie l'appartenance
        au dossier — comparer les chaînes avant résolution ne protège de
        rien.
        """
        root = Path(getattr(settings, "SOURCING_IMPORT_DIR", Path(settings.BASE_DIR) / "imports"))
        root = root.resolve()
        candidate = (root / (self.source.endpoint or "")).resolve()
        if not candidate.is_relative_to(root):
            raise AdapterError(f"Le fichier doit se trouver dans {root}.")
        if not candidate.is_file():
            raise AdapterError(f"Fichier absent : {candidate}")
        return candidate
