from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.analytics.services import record_contact_event, record_product_view, record_search_event

from .filters import ProductFilter, apply_attribute_filters
from .models import Category, Favorite, Product, ProductImage
from .permissions import IsImageOwnerOrReadOnly, IsOwnerSupplierOrReadOnly, IsSupplier
from .serializers import (
    CategorySerializer,
    FavoriteSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductImageUpdateSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
)
from .tasks import compress_product_image_task
from apps.media.validators import validate_image_upload


def _is_owner(user, product):
    if not user.is_authenticated:
        return False
    profile = getattr(user, "supplier_profile", None)
    return profile is not None and product.supplier_id == profile.pk


class CategoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only: categories are administered via /admin/ (Phase moderation)."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs.filter(parent__isnull=True)  # children come nested
        return qs


class ProductViewSet(viewsets.ModelViewSet):
    filterset_class = ProductFilter
    search_fields = ["title", "description", "city"]
    ordering_fields = ["price", "created_at", "views_count"]
    ordering = ["-created_at"]
    lookup_field = "slug"

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsSupplier()]
        if self.action in ("update", "partial_update", "destroy", "upload_images", "toggle_active"):
            return [permissions.IsAuthenticated(), IsOwnerSupplierOrReadOnly()]
        if self.action in ("contact", "toggle_favorite"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_throttles(self):
        # Only the listing endpoint carries the tighter "search" budget:
        # browsing individual pages must not trip a scraping limit.
        if self.action == "list":
            self.throttle_scope = "search"
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductWriteSerializer

    def get_queryset(self):
        qs = Product.objects.select_related("category", "supplier__user").prefetch_related("images")
        user = self.request.user
        if self.action == "list":
            if self.request.query_params.get("mine") == "true" and user.is_authenticated:
                qs = qs.filter(supplier__user=user)
            else:
                qs = qs.filter(status=Product.Status.APPROVED, is_active=True)
            return apply_attribute_filters(qs, self.request.query_params)
        if self.action == "retrieve":
            qs = qs.prefetch_related("attribute_values__attribute")
        # retrieve/update/destroy: owner & staff may reach non-approved objects;
        # everyone else gets 404 (never reveal a pending/rejected listing exists).
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # One query for the whole page instead of one `is_favorite` check per card.
        if self.action == "list" and self.request.user.is_authenticated:
            context["favorited_product_ids"] = set(
                Favorite.objects.filter(user=self.request.user).values_list("product_id", flat=True)
            )
        return context

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), slug=self.kwargs["slug"])
        user = self.request.user
        publicly_visible = obj.status == Product.Status.APPROVED and obj.is_active
        if not publicly_visible and not (_is_owner(user, obj) or user.is_staff):
            raise Http404
        self.check_object_permissions(self.request, obj)
        return obj

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if request.query_params.get("mine") != "true":
            ignored = {"page", "page_size", "ordering", "search", "mine"}
            filters = {k: v for k, v in request.query_params.items() if k not in ignored}
            count = response.data.get("count", 0) if isinstance(response.data, dict) else len(response.data)
            record_search_event(
                request,
                query=request.query_params.get("search", ""),
                filters=filters,
                results_count=count,
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not _is_owner(request.user, instance):
            record_product_view(request, instance)
            instance.refresh_from_db(fields=["views_count"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(
            supplier=self.request.user.supplier_profile,
            status=Product.Status.PENDING,
        )

    def perform_update(self, serializer):
        # Any content edit re-enters moderation (mirrors the SSR flow it replaces).
        serializer.save(status=Product.Status.PENDING, published_at=None)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_images(self, request, slug=None):
        product = self.get_object()
        files = request.FILES.getlist("images")
        if not files:
            return Response({"images": ["Aucun fichier reçu."]}, status=status.HTTP_400_BAD_REQUEST)

        # Validate every file before writing any of them, so a bad file in
        # the batch can't leave the product with a half-uploaded gallery.
        errors = []
        for uploaded in files:
            try:
                validate_image_upload(uploaded)
            except DjangoValidationError as exc:
                errors.extend(exc.messages)
        if errors:
            return Response({"images": errors}, status=status.HTTP_400_BAD_REQUEST)

        has_cover = product.images.filter(is_cover=True).exists()
        start_order = product.images.count()
        created = []
        for idx, f in enumerate(files):
            image = ProductImage.objects.create(
                product=product,
                image=f,
                # `master` is written by the compression step, from an
                # optimised rendition rather than the raw upload: a later
                # crop starts from 1600px, not from 12 MB of phone photo.
                order=start_order + idx,
                is_cover=not has_cover and idx == 0,
            )
            compress_product_image_task.delay(image.pk)
            created.append(image)

        serializer = ProductImageSerializer(created, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def contact(self, request, slug=None):
        """Reveal the supplier's contact details and log the interaction.

        Separate from `retrieve` so the dashboard's "Contacts" stat only
        counts genuine intent to reach out, not every page view.
        """
        product = self.get_object()
        channel = request.data.get("channel", "phone")
        if channel not in ("phone", "whatsapp"):
            channel = "phone"
        if not _is_owner(request.user, product):
            record_contact_event(request, product, channel=channel)
        serializer = ProductDetailSerializer(product, context={"request": request})
        return Response({
            "phone": serializer.data["supplier"]["phone"],
            "whatsapp_number": serializer.data["supplier"]["whatsapp_number"],
        })

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def share(self, request, slug=None):
        product = self.get_object()
        type(product).objects.filter(pk=product.pk).update(shares_count=models.F("shares_count") + 1)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def toggle_favorite(self, request, slug=None):
        product = self.get_object()
        favorite = Favorite.objects.filter(user=request.user, product=product).first()
        if favorite:
            favorite.delete()
            return Response({"is_favorite": False})
        Favorite.objects.create(user=request.user, product=product)
        return Response({"is_favorite": True}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, slug=None):
        product = self.get_object()
        if product.status != Product.Status.APPROVED:
            return Response(
                {"detail": "Seule une annonce approuvée peut être publiée/dépubliée."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])
        return Response(ProductDetailSerializer(product, context={"request": request}).data)


class FavoriteViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """The signed-in user's favourites. Creation goes through
    `POST /products/{slug}/toggle_favorite/`."""

    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Scoped to the requester: a favourite id from someone else 404s.
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product__category", "product__supplier__user")
            .prefetch_related("product__images")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["favorited_product_ids"] = set(
            self.get_queryset().values_list("product_id", flat=True)
        )
        return context

    @action(detail=False, methods=["get"])
    def slugs(self, request):
        """Just the favourited slugs, for the heart buttons.

        Pages are server-rendered and the SSR fetch is anonymous, so
        `is_favorite` is always false in the initial HTML. The browser
        reconciles the hearts with this one small call instead of the client
        re-fetching every product it displays.
        """
        slugs = list(
            Favorite.objects.filter(user=request.user).values_list("product__slug", flat=True)
        )
        return Response({"slugs": slugs})


class ProductImageViewSet(
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Reordering / choosing the cover / deleting a single image."""

    queryset = ProductImage.objects.select_related("product__supplier")
    serializer_class = ProductImageUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsImageOwnerOrReadOnly]
    http_method_names = ["get", "patch", "post", "delete"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductImageSerializer
        return ProductImageUpdateSerializer

    def perform_update(self, serializer):
        image = serializer.save()
        if image.is_cover:
            image.product.images.exclude(pk=image.pk).update(is_cover=False)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def replace(self, request, pk=None):
        """Swap the rendered file of an already-published image.

        Used by the in-browser editor (crop / rotate / flip): the client
        sends the edited bitmap, the untouched `master` is preserved so the
        next edit can still start from the original.
        """
        image = self.get_object()
        uploaded = request.FILES.get("image")
        if not uploaded:
            return Response({"image": ["Aucun fichier reçu."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_image_upload(uploaded)
        except DjangoValidationError as exc:
            return Response({"image": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        if not image.master:
            # Existing rows created before master-keeping: adopt the current
            # file as the master before overwriting it.
            image.master = image.image

        image.image = uploaded
        image.save(update_fields=["image", "master"])
        compress_product_image_task.delay(image.pk)
        image.refresh_from_db()
        return Response(ProductImageSerializer(image, context={"request": request}).data)
