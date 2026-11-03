"""Ce que « une annonce publique » veut dire, en un seul endroit.

La règle a changé trois fois : approuvée, puis approuvée et active, puis —
au lancement « location » — approuvée, active et en location. Chaque fois,
une requête oubliée quelque part a continué de montrer ce qu'il ne fallait
plus. La dernière en date : les sections de découverte de la page d'accueil
proposaient encore des annonces de vente alors que le catalogue n'en
montrait plus.

Un seul appel à `public_products()` et l'oubli n'est plus possible.
"""
from django.conf import settings

from .models import Product


def public_products():
    """Le jeu d'annonces qu'un visiteur a le droit de voir."""
    queryset = Product.objects.filter(status=Product.Status.APPROVED, is_active=True)
    if settings.LAUNCH_RENTAL_ONLY:
        queryset = queryset.filter(listing_type=Product.ListingType.RENT)
    return queryset
