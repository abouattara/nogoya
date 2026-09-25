from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Product

from .models import LiveMessage, LiveProduct, LiveSession, LiveViewer
from .serializers import (
    LiveMessageSerializer,
    LiveProductSerializer,
    LiveSessionSerializer,
    LiveSessionWriteSerializer,
)


class IsLiveHost(permissions.BasePermission):
    """Only the host may change the live itself.

    Deliberately *not* applied to viewer-facing actions (join/leave/chat):
    those are open to the audience and guard themselves.
    """

    message = "Seul l'hôte du live peut le modifier."

    def has_object_permission(self, request, view, obj):
        return obj.host_id == request.user.id or request.user.is_staff


# Actions that mutate the live session itself.
HOST_ACTIONS = {"update", "partial_update", "destroy", "start", "end", "pin_product", "unpin_product"}


class LiveSessionViewSet(viewsets.ModelViewSet):
    """Live sessions — business layer only, no video infrastructure yet.

    A provider (LiveKit, Cloudflare Stream...) plugs into `start()` by
    filling `provider`, `provider_session_id`, `ingest_url` and
    `playback_url`; nothing else here needs to change. See LIVE.md.
    """

    def get_permissions(self):
        if self.action in HOST_ACTIONS:
            return [permissions.IsAuthenticated(), IsLiveHost()]
        if self.action in ("join", "leave", "list", "retrieve"):
            return [permissions.AllowAny()]
        # create / products / messages: authenticated writes, public reads.
        # The host-only parts of `products` are enforced inside the handler.
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LiveSessionWriteSerializer
        return LiveSessionSerializer

    def get_queryset(self):
        qs = LiveSession.objects.select_related("host").prefetch_related(
            "live_products__product__images", "live_products__product__supplier__user"
        )
        if self.action == "list":
            if self.request.query_params.get("mine") == "true" and self.request.user.is_authenticated:
                return qs.filter(host=self.request.user)
            # Drafts stay private to their host.
            return qs.exclude(status=LiveSession.Status.DRAFT)
        return qs

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    def create(self, request, *args, **kwargs):
        return self._write_then_read(super().create(request, *args, **kwargs))

    def update(self, request, *args, **kwargs):
        return self._write_then_read(super().update(request, *args, **kwargs))

    def _write_then_read(self, response):
        """Answer writes with the full session, not the narrow write payload.

        The write serializer only carries the editable fields, so a client
        creating a live got back a body without `status`, `host` or
        `playback_url` and had to immediately re-fetch the session.
        """
        live = self.get_queryset().get(pk=response.data["id"])
        response.data = LiveSessionSerializer(live, context=self.get_serializer_context()).data
        return response

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        live = self.get_object()
        if live.status in (LiveSession.Status.ENDED, LiveSession.Status.CANCELLED):
            return Response({"detail": "Ce live est terminé."}, status=status.HTTP_400_BAD_REQUEST)
        live.start()
        return Response(LiveSessionSerializer(live, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        live = self.get_object()
        if live.status != LiveSession.Status.LIVE:
            return Response({"detail": "Ce live n'est pas en cours."}, status=status.HTTP_400_BAD_REQUEST)
        live.end()
        return Response(LiveSessionSerializer(live, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def join(self, request, pk=None):
        live = self.get_object()
        if live.status != LiveSession.Status.LIVE:
            return Response({"detail": "Ce live n'est pas en cours."}, status=status.HTTP_400_BAD_REQUEST)
        LiveViewer.objects.create(
            live=live,
            user=request.user if request.user.is_authenticated else None,
            visitor_id="" if request.user.is_authenticated else getattr(request, "visitor_id", ""),
        )
        current = live.current_viewers
        if current > live.peak_viewers:
            live.peak_viewers = current
            live.save(update_fields=["peak_viewers"])
        return Response({"viewers": current})

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def leave(self, request, pk=None):
        live = self.get_object()
        viewers = live.viewers.filter(left_at__isnull=True)
        if request.user.is_authenticated:
            viewers = viewers.filter(user=request.user)
        else:
            viewers = viewers.filter(visitor_id=getattr(request, "visitor_id", ""))
        viewers.update(left_at=timezone.now())
        return Response({"viewers": live.current_viewers})

    @action(detail=True, methods=["get", "post"], url_path="products")
    def products(self, request, pk=None):
        live = self.get_object()
        if request.method == "POST":
            if live.host_id != request.user.id and not request.user.is_staff:
                return Response({"detail": "Seul l'hôte peut ajouter un produit."}, status=status.HTTP_403_FORBIDDEN)
            product = get_object_or_404(Product, pk=request.data.get("product"))
            if product.supplier.user_id != live.host_id:
                return Response(
                    {"detail": "Vous ne pouvez présenter que vos propres annonces."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            link, created = LiveProduct.objects.get_or_create(
                live=live, product=product,
                defaults={"position": live.live_products.count()},
            )
            serializer = LiveProductSerializer(link, context={"request": request})
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        serializer = LiveProductSerializer(
            live.live_products.all(), many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="products/(?P<product_pk>[^/.]+)/pin")
    def pin_product(self, request, pk=None, product_pk=None):
        live = self.get_object()
        if live.host_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Seul l'hôte peut épingler un produit."}, status=status.HTTP_403_FORBIDDEN)
        link = get_object_or_404(LiveProduct, live=live, product_id=product_pk)
        link.feature()
        return Response(LiveProductSerializer(link, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="products/(?P<product_pk>[^/.]+)/unpin")
    def unpin_product(self, request, pk=None, product_pk=None):
        live = self.get_object()
        if live.host_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "Seul l'hôte peut retirer un produit."}, status=status.HTTP_403_FORBIDDEN)
        link = get_object_or_404(LiveProduct, live=live, product_id=product_pk)
        link.unfeature()
        return Response(LiveProductSerializer(link, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        live = self.get_object()
        if request.method == "POST":
            if not request.user.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            serializer = LiveMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            message = serializer.save(live=live, sender=request.user)
            return Response(
                LiveMessageSerializer(message, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        page = self.paginate_queryset(
            LiveMessage.objects.filter(live=live).select_related("sender", "product")
        )
        serializer = LiveMessageSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)
