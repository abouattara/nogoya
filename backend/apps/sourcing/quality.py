"""Ce qu'une annonce doit avoir pour mériter une place dans le catalogue.

Un refus n'est pas une perte : la ligne reste dans `ListingImport` avec son
motif, visible en administration. Un humain peut compléter puis publier.
Ce qui serait une perte, c'est de publier une annonce sans prix ni ville :
elle pollue la recherche, déçoit le visiteur, et personne ne saura dire
d'où venait l'erreur.
"""
from apps.catalog.models import Product

MIN_TITLE_LENGTH = 8
MAX_PLAUSIBLE_PRICE = 10_000_000_000  # 10 milliards de FCFA : une faute de saisie


def check(normalized, *, source):
    """Renvoie la liste des motifs de refus. Vide = l'annonce passe."""
    problems = []

    title = (normalized.get("title") or "").strip()
    if len(title) < MIN_TITLE_LENGTH:
        problems.append("Titre absent ou trop court.")

    if not (normalized.get("city") or "").strip():
        problems.append("Ville absente : l'annonce serait introuvable à la recherche.")

    price = normalized.get("price")
    if price is None:
        problems.append("Prix absent ou illisible.")
    elif price <= 0:
        problems.append("Prix nul ou négatif.")
    elif price > MAX_PLAUSIBLE_PRICE:
        problems.append(f"Prix invraisemblable ({price}).")

    if normalized.get("category_id") is None:
        problems.append("Catégorie non reconnue : à rattacher à la main.")

    listing_type = normalized.get("listing_type")
    if listing_type not in dict(Product.ListingType.choices):
        problems.append(f"Type d'annonce inconnu : {listing_type!r}.")

    # Une annonce référencée sans lien de retour n'a pas d'intérêt : le
    # visiteur ne pourrait rien en faire, et NOGOYA ne peut pas la louer.
    if source.kind != source.Kind.FILE and not (normalized.get("original_url") or "").strip():
        problems.append("Aucun lien vers l'annonce d'origine.")

    return problems
