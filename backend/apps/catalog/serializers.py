from django.db import transaction
from rest_framework import serializers

from apps.suppliers.serializers import SupplierPublicSerializer

from .models import (
    Category,
    CategoryAttribute,
    Favorite,
    Product,
    ProductAttributeValue,
    ProductImage,
)


class CategoryAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryAttribute
        fields = [
            "id", "name", "slug", "attribute_type", "required",
            "filterable", "searchable", "unit", "options", "position",
        ]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "order", "parent", "children", "attributes"]

    def get_children(self, obj):
        # Shallow tree (2 levels) is enough for nav/filter UI; deeper nesting
        # would need a smarter query (django-mptt) if categories grow a lot.
        return CategorySerializer(obj.children.all(), many=True, context=self.context).data

    def get_attributes(self, obj):
        return CategoryAttributeSerializer(obj.effective_attributes(), many=True).data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_cover", "order", "width", "height"]
        read_only_fields = ["width", "height"]


class ProductImageUpdateSerializer(serializers.ModelSerializer):
    """Reordering / cover selection only — never re-uploads image bytes here."""

    class Meta:
        model = ProductImage
        fields = ["id", "is_cover", "order"]


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="attribute.slug", read_only=True)
    name = serializers.CharField(source="attribute.name", read_only=True)
    attribute_type = serializers.CharField(source="attribute.attribute_type", read_only=True)
    unit = serializers.CharField(source="attribute.unit", read_only=True)

    class Meta:
        model = ProductAttributeValue
        fields = ["slug", "name", "attribute_type", "unit", "value"]


class ProductListSerializer(serializers.ModelSerializer):
    """Trimmed-down payload for listing/search results (card view)."""

    cover_image = serializers.SerializerMethodField()
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    supplier_name = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "title", "slug", "category", "price", "currency",
            "listing_type", "rental_period", "city", "cover_image",
            "views_count", "shares_count", "supplier_name", "status", "is_active",
            "is_favorite", "created_at",
        ]

    def get_cover_image(self, obj):
        image = obj.cover_image
        if not image:
            return None
        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url

    def get_supplier_name(self, obj):
        user = obj.supplier.user
        return user.get_full_name() or user.phone

    def get_is_favorite(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # `favorited_product_ids` is injected by the viewset to keep this a
        # single query for a whole page of results instead of one per card.
        cached = self.context.get("favorited_product_ids")
        if cached is not None:
            return obj.pk in cached
        return Favorite.objects.filter(user=request.user, product=obj).exists()


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    supplier = SupplierPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    map_url = serializers.ReadOnlyField()
    attributes = ProductAttributeValueSerializer(source="attribute_values", many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "supplier", "images", "published_at",
            "location", "region", "country", "latitude", "longitude",
            "location_precision", "map_url", "attributes",
        ]

    def get_latitude(self, obj):
        return obj.public_latitude

    def get_longitude(self, obj):
        return obj.public_longitude


class ProductWriteSerializer(serializers.ModelSerializer):
    """Create/update payload — ownership + moderation state are set server-side.

    ``slug`` is exposed read-only so the client can immediately follow up
    with the image-upload call without a second round trip to fetch it.
    ``attributes`` is a {attribute_slug: value} map validated against the
    selected category's attribute definitions.
    """

    attributes = serializers.DictField(required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "category", "description", "price", "currency",
            "listing_type", "rental_period", "city", "location", "region", "country",
            "latitude", "longitude", "place_id", "location_precision", "attributes",
        ]
        read_only_fields = ["slug"]

    def validate_category(self, value):
        if value is not None and value.children.exists():
            raise serializers.ValidationError(
                "Choisissez une sous-catégorie précise, pas une catégorie parente."
            )
        return value

    def validate(self, attrs):
        category = attrs.get("category") or getattr(self.instance, "category", None)
        raw = attrs.get("attributes")
        if raw is None:
            return attrs
        if category is None:
            raise serializers.ValidationError({"attributes": "Choisissez d'abord une catégorie."})

        definitions = {a.slug: a for a in category.effective_attributes()}
        unknown = set(raw) - set(definitions)
        if unknown:
            raise serializers.ValidationError(
                {"attributes": f"Attributs inconnus pour cette catégorie : {', '.join(sorted(unknown))}"}
            )

        cleaned = {}
        errors = {}
        for slug, definition in definitions.items():
            provided = raw.get(slug, None)
            is_empty = provided in (None, "", [])
            if is_empty:
                if definition.required:
                    errors[slug] = f"« {definition.name} » est obligatoire."
                continue
            try:
                cleaned[slug] = _coerce_attribute_value(definition, provided)
            except ValueError as exc:
                errors[slug] = str(exc)
        if errors:
            raise serializers.ValidationError({"attributes": errors})

        attrs["attributes"] = cleaned
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        attribute_values = validated_data.pop("attributes", None)
        product = super().create(validated_data)
        if attribute_values is not None:
            _sync_attribute_values(product, attribute_values)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        attribute_values = validated_data.pop("attributes", None)
        product = super().update(instance, validated_data)
        if attribute_values is not None:
            _sync_attribute_values(product, attribute_values)
        return product


def _coerce_attribute_value(definition, value):
    """Validate + normalise a raw attribute value against its declared type."""
    kind = definition.attribute_type
    types = CategoryAttribute.AttributeType

    if kind == types.NUMBER:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"« {definition.name} » doit être un nombre.")

    if kind == types.BOOLEAN:
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("true", "1", "oui", "yes"):
            return True
        if str(value).lower() in ("false", "0", "non", "no"):
            return False
        raise ValueError(f"« {definition.name} » doit être oui ou non.")

    if kind == types.SELECT:
        if str(value) not in [str(o) for o in definition.options]:
            raise ValueError(f"« {value} » n'est pas une option de « {definition.name} ».")
        return str(value)

    if kind == types.MULTI_SELECT:
        values = value if isinstance(value, (list, tuple)) else [value]
        allowed = [str(o) for o in definition.options]
        invalid = [str(v) for v in values if str(v) not in allowed]
        if invalid:
            raise ValueError(f"Options invalides pour « {definition.name} » : {', '.join(invalid)}")
        return [str(v) for v in values]

    if kind == types.DATE:
        from django.utils.dateparse import parse_date

        if parse_date(str(value)) is None:
            raise ValueError(f"« {definition.name} » doit être une date (AAAA-MM-JJ).")
        return str(value)

    return str(value)


def _sync_attribute_values(product, cleaned):
    """Replace the product's attribute values with `cleaned` (slug -> value)."""
    definitions = {a.slug: a for a in product.category.effective_attributes()}
    product.attribute_values.exclude(attribute__slug__in=cleaned.keys()).delete()
    for slug, value in cleaned.items():
        definition = definitions[slug]
        obj, _ = ProductAttributeValue.objects.get_or_create(
            product=product, attribute=definition, defaults={"value": value}
        )
        if obj.value != value:
            obj.value = value
        obj.save()


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "product", "created_at"]
