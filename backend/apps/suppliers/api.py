from django.db.models import Sum

from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.analytics.aggregates import supplier_analytics
from apps.analytics.models import ContactEvent
from apps.catalog.models import Product
from apps.messaging.services import unread_count_for

from .models import SupplierProfile
from .serializers import SupplierMeSerializer, SupplierPublicSerializer


class SupplierViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Public, read-only supplier directory + catalog pages."""

    queryset = SupplierProfile.objects.select_related("user")
    serializer_class = SupplierPublicSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get", "patch"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        try:
            profile = request.user.supplier_profile
        except SupplierProfile.DoesNotExist:
            return Response({"detail": "Ce compte n'est pas un fournisseur."}, status=403)

        if request.method == "PATCH":
            serializer = SupplierMeSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(SupplierMeSerializer(profile).data)

    @action(detail=False, methods=["get"], url_path="me/stats", permission_classes=[permissions.IsAuthenticated])
    def stats(self, request):
        try:
            profile = request.user.supplier_profile
        except SupplierProfile.DoesNotExist:
            return Response({"detail": "Ce compte n'est pas un fournisseur."}, status=403)

        products = Product.objects.filter(supplier=profile)
        aggregates = products.aggregate(
            total_views=Sum("views_count"), total_shares=Sum("shares_count")
        )
        return Response({
            "products_online": products.filter(status=Product.Status.APPROVED, is_active=True).count(),
            "products_total": products.count(),
            "total_views": aggregates["total_views"] or 0,
            "total_shares": aggregates["total_shares"] or 0,
            "total_contacts": ContactEvent.objects.filter(product__supplier=profile).count(),
            "unread_messages": unread_count_for(request.user),
        })

    @action(detail=False, methods=["get"], url_path="me/analytics", permission_classes=[permissions.IsAuthenticated])
    def analytics(self, request):
        """Time series for the dashboard charts — own data only."""
        try:
            profile = request.user.supplier_profile
        except SupplierProfile.DoesNotExist:
            return Response({"detail": "Ce compte n'est pas un fournisseur."}, status=403)

        try:
            days = min(max(int(request.query_params.get("days", 30)), 7), 365)
        except ValueError:
            days = 30
        return Response(supplier_analytics(profile, days=days))
