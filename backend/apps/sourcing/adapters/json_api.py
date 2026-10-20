"""Une API JSON de partenaire.

Générique à dessein : tant qu'aucune API ne nous est ouverte, écrire un
adaptateur par partenaire imaginaire serait du code mort. Celui-ci lit un
point d'accès, descend jusqu'au tableau d'annonces (`config["items_path"]`)
et applique la correspondance de champs. Un vrai partenaire se branche en
remplissant la configuration, sans déploiement.

La clé d'API, lorsqu'il y en a une, est lue dans la variable
d'environnement nommée par `credential_env_var`. Elle n'est ni en base, ni
dans le dépôt.

**Aucune API d'annonces n'est connectée à ce jour.** Rien ici ne suppose le
contraire : sans `endpoint` configuré, l'adaptateur refuse de s'exécuter.
"""
import json
from datetime import timezone as dt_timezone
from datetime import datetime

from ..net import FetchFailed, UnsafeUrl, fetch
from .base import AdapterError, RawListing, SourceAdapter, register


@register
class JsonApiAdapter(SourceAdapter):
    key = "api"

    def fetch(self):
        if not self.source.endpoint:
            raise AdapterError("Aucun point d'accès configuré.")

        headers = dict(self.config.get("headers") or {})
        secret = self.source.credential
        if self.source.credential_env_var and not secret:
            raise AdapterError(
                f"La variable d'environnement {self.source.credential_env_var} est vide : "
                "la clé n'est pas configurée sur ce serveur."
            )
        if secret:
            template = self.config.get("auth_header_template", "Bearer {key}")
            headers[self.config.get("auth_header", "Authorization")] = template.format(key=secret)

        try:
            payload = fetch(self.source.endpoint, headers=headers)
        except (UnsafeUrl, FetchFailed) as exc:
            raise AdapterError(str(exc)) from exc

        try:
            document = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"Réponse JSON illisible : {exc}") from exc

        collected = datetime.now(dt_timezone.utc)
        for item in self._items(document):
            if not isinstance(item, dict):
                continue
            images = self.mapped(item, "image_urls", []) or []
            if isinstance(images, str):
                images = [u.strip() for u in images.split("|") if u.strip()]
            yield RawListing(
                external_id=_as_text(self.mapped(item, "external_id")),
                original_url=self.mapped(item, "original_url"),
                title=self.mapped(item, "title"),
                description=self.mapped(item, "description"),
                price_text=_as_text(self.mapped(item, "price_text")),
                currency=self.mapped(item, "currency"),
                price_period=self.mapped(item, "price_period"),
                listing_type=self.mapped(item, "listing_type"),
                category_hint=self.mapped(item, "category"),
                city=self.mapped(item, "city"),
                area=self.mapped(item, "area"),
                region=self.mapped(item, "region"),
                country=self.mapped(item, "country"),
                image_urls=[str(u) for u in images],
                contact_public=self.mapped(item, "contact_public"),
                collected_at=collected,
                raw=item,
            )

    def _items(self, document):
        """Descend `config["items_path"]` — « data.results » par exemple."""
        path = self.config.get("items_path", "")
        node = document
        for step in filter(None, path.split(".")):
            if not isinstance(node, dict) or step not in node:
                raise AdapterError(f"Chemin « {path} » absent de la réponse.")
            node = node[step]
        if not isinstance(node, list):
            raise AdapterError("Le chemin configuré ne désigne pas une liste d'annonces.")
        return node


def _as_text(value):
    return None if value is None else str(value)
