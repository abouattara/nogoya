from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Favorite
from apps.catalog.serializers import ProductListSerializer

from .recommendations import (
    new_arrivals,
    recent_searches,
    recently_viewed_products,
    recommended_products,
)


class DiscoveryViewSet(viewsets.ViewSet):
    """Personalised home-page sections.

    Works for anonymous visitors too (keyed on the `nogoya_vid` cookie), so
    the discovery experience does not require an account.
    """

    permission_classes = [permissions.AllowAny]

    def _serialize(self, products, request):
        favorited = set()
        if request.user.is_authenticated:
            favorited = set(
                Favorite.objects.filter(user=request.user).values_list("product_id", flat=True)
            )
        return ProductListSerializer(
            products, many=True,
            context={"request": request, "favorited_product_ids": favorited},
        ).data

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response({
            "recently_viewed": self._serialize(recently_viewed_products(request), request),
            "recommended": self._serialize(recommended_products(request), request),
            "new_arrivals": self._serialize(new_arrivals(request), request),
            "recent_searches": recent_searches(request),
        })
