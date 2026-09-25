import django_filters as filters

from .models import CategoryAttribute, Product


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    city = filters.CharFilter(field_name="city", lookup_expr="iexact")
    listing_type = filters.ChoiceFilter(choices=Product.ListingType.choices)
    supplier = filters.NumberFilter(field_name="supplier_id")
    price_min = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="price", lookup_expr="lte")
    favorites = filters.BooleanFilter(method="filter_favorites")

    class Meta:
        model = Product
        fields = ["category", "city", "listing_type", "supplier", "price_min", "price_max"]

    def filter_favorites(self, queryset, name, value):
        user = getattr(self.request, "user", None)
        if not value or not user or not user.is_authenticated:
            return queryset
        return queryset.filter(favorited_by__user=user)


def apply_attribute_filters(queryset, query_params):
    """Narrow a product queryset with `attr_<slug>=value` query parameters.

    Only attributes explicitly marked `filterable` are honoured, so a
    supplier cannot turn an internal attribute into a public filter.
    Numeric attributes additionally accept `attr_<slug>_min` / `_max`.
    """
    filterable = {
        a.slug: a for a in CategoryAttribute.objects.filter(filterable=True)
    }
    if not filterable:
        return queryset

    for key, raw in query_params.items():
        if not key.startswith("attr_") or raw in (None, ""):
            continue
        name = key[len("attr_"):]
        bound = None
        if name.endswith("_min") and name[:-4] in filterable:
            name, bound = name[:-4], "min"
        elif name.endswith("_max") and name[:-4] in filterable:
            name, bound = name[:-4], "max"
        definition = filterable.get(name)
        if definition is None:
            continue

        if bound == "min":
            try:
                queryset = queryset.filter(
                    attribute_values__attribute=definition,
                    attribute_values__numeric_value__gte=float(raw),
                )
            except ValueError:
                continue
        elif bound == "max":
            try:
                queryset = queryset.filter(
                    attribute_values__attribute=definition,
                    attribute_values__numeric_value__lte=float(raw),
                )
            except ValueError:
                continue
        elif definition.attribute_type == CategoryAttribute.AttributeType.MULTI_SELECT:
            queryset = queryset.filter(
                attribute_values__attribute=definition,
                attribute_values__value__contains=raw,
            )
        elif definition.attribute_type == CategoryAttribute.AttributeType.BOOLEAN:
            wanted = str(raw).lower() in ("true", "1", "oui", "yes")
            queryset = queryset.filter(
                attribute_values__attribute=definition,
                attribute_values__value=wanted,
            )
        elif definition.attribute_type == CategoryAttribute.AttributeType.NUMBER:
            try:
                queryset = queryset.filter(
                    attribute_values__attribute=definition,
                    attribute_values__numeric_value=float(raw),
                )
            except ValueError:
                continue
        else:
            queryset = queryset.filter(
                attribute_values__attribute=definition,
                attribute_values__value=str(raw),
            )
    return queryset.distinct()
