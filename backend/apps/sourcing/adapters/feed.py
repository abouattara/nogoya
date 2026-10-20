"""Un flux RSS ou Atom.

Beaucoup de sites d'annonces publient un flux : c'est, par construction, du
contenu que l'éditeur met à disposition pour être relayé. Cela ne vaut pas
autorisation de tout recopier — d'où le renvoi systématique vers le lien
d'origine, et les photos qui ne sont reprises que si la source l'autorise
explicitement (`allows_image_reuse`).

Analyse avec `xml.etree` de la bibliothèque standard plutôt que feedparser :
le projet tient à son nombre de dépendances, et un flux reste du XML.
"""
from datetime import timezone as dt_timezone
from datetime import datetime
from xml.etree import ElementTree

from ..net import FetchFailed, UnsafeUrl, fetch
from .base import AdapterError, RawListing, SourceAdapter, register

_ATOM = "{http://www.w3.org/2005/Atom}"


@register
class FeedAdapter(SourceAdapter):
    key = "feed"

    def fetch(self):
        if not self.source.endpoint:
            raise AdapterError("Aucune URL de flux configurée.")
        try:
            payload = fetch(self.source.endpoint)
        except (UnsafeUrl, FetchFailed) as exc:
            raise AdapterError(str(exc)) from exc

        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise AdapterError(f"Flux illisible : {exc}") from exc

        collected = datetime.now(dt_timezone.utc)
        entries = root.findall(".//item") or root.findall(f".//{_ATOM}entry")
        if not entries:
            raise AdapterError("Flux sans entrée : ni <item> RSS ni <entry> Atom.")

        for entry in entries:
            yield self._to_listing(entry, collected)

    def _to_listing(self, entry, collected):
        title = _text(entry, "title") or _text(entry, f"{_ATOM}title")
        description = _text(entry, "description") or _text(entry, f"{_ATOM}summary")
        link = _text(entry, "link") or _link_attr(entry)
        guid = _text(entry, "guid") or _text(entry, f"{_ATOM}id")

        # Un flux ne porte pas de champs métier : le prix et la ville sont
        # cherchés dans le texte, et restent vides si on ne les y trouve
        # pas. Le contrôle qualité renverra l'annonce en examen manuel.
        return RawListing(
            external_id=guid,
            original_url=link,
            title=title,
            description=description,
            price_text=description,
            category_hint=self.config.get("category_hint"),
            city=self.config.get("city"),
            country=self.config.get("country") or "Burkina Faso",
            listing_type=self.config.get("listing_type"),
            collected_at=collected,
            raw={"title": title, "link": link, "guid": guid},
        )


def _text(node, tag):
    found = node.find(tag)
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _link_attr(entry):
    link = entry.find(f"{_ATOM}link")
    return link.get("href") if link is not None else None
