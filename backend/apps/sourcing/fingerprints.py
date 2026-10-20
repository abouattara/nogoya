"""Reconnaître une annonce déjà vue, sans confondre deux biens voisins.

Deux niveaux, parce que les deux questions sont différentes :

* `fingerprint()` répond à « est-ce la même annonce chez la même source ? ».
  La réponse doit être stable d'une exécution à l'autre, sinon chaque import
  recrée tout. On s'appuie sur ce que la source garantit : son identifiant,
  sinon l'URL.

* `find_probable_duplicate()` répond à « ce bien existe-t-il déjà dans le
  catalogue, venu d'ailleurs ? ». La réponse est un soupçon, jamais une
  certitude : on signale, on ne fusionne pas.

Le titre seul ne décide de rien. « Appartement 2 chambres à Ouaga 2000 »
peut désigner cinquante biens distincts. Il ne compte que combiné à la
ville, à la catégorie et au prix — et même là, le résultat part en examen
manuel.
"""
import hashlib

from apps.catalog.models import Product

from .normalization import normalize_text, normalize_url


def fingerprint(*, external_id=None, original_url=None, title=None, city=None, price=None, category_id=None):
    """Clé stable d'une annonce chez une source donnée."""
    if external_id:
        basis = f"id:{str(external_id).strip()}"
    elif original_url:
        basis = f"url:{normalize_url(original_url)}"
    else:
        # Dernier recours : un fichier CSV sans identifiant ni lien. La clé
        # porte alors sur ce qui distingue vraiment deux biens.
        basis = "fields:" + "|".join(
            [
                normalize_text(title),
                normalize_text(city),
                str(category_id or ""),
                str(price or ""),
            ]
        )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def find_probable_duplicate(*, title, city, price, category_id, exclude_product_id=None):
    """Un produit existant qui pourrait être le même bien, ou None.

    Trois signaux doivent concorder : la ville, la catégorie et le prix —
    puis le titre doit se recouper suffisamment. Un seul signal ne suffit
    jamais.
    """
    if not city or price is None:
        return None

    candidates = Product.objects.filter(city__iexact=city, price=price)
    if category_id:
        candidates = candidates.filter(category_id=category_id)
    if exclude_product_id:
        candidates = candidates.exclude(pk=exclude_product_id)

    wanted = set(normalize_text(title).split())
    if not wanted:
        return None

    for candidate in candidates.only("id", "title")[:50]:
        other = set(normalize_text(candidate.title).split())
        if not other:
            continue
        overlap = len(wanted & other) / len(wanted | other)
        if overlap >= 0.6:
            return candidate
    return None
