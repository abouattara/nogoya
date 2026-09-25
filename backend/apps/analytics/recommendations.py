"""Recommendation engine, MVP version.

Deliberately rule-based (history + categories + favourites + city), not ML:
it works from day one on a small dataset, and `recommended_products` is the
single seam a smarter engine would replace later.
"""
from django.db.models import Count, Q

from apps.catalog.models import Favorite, Product

from .models import ProductView, SearchEvent


def _visitor_scope(request):
    """Rows belonging to this user, or to this browser's anonymous id.

    A signed-in visitor matches both: pages are server-rendered, so the
    browsing Django sees (product views, searches) is recorded without a user
    and carries only the visitor id. Ignoring it left "Vus récemment" empty
    for exactly the people who were signed in. The id is rotated on logout so
    a shared browser never shows one account's history to the next.
    """
    visitor_id = getattr(request, "visitor_id", "")
    visitor_scope = Q(visitor_id=visitor_id) if visitor_id else None
    if not request.user.is_authenticated:
        return visitor_scope if visitor_scope is not None else Q(pk__isnull=True)
    scope = Q(user=request.user)
    return scope | visitor_scope if visitor_scope is not None else scope


def recently_viewed_products(request, limit=8):
    scope = _visitor_scope(request)
    viewed_ids = (
        ProductView.objects.filter(scope)
        .order_by("-created_at")
        .values_list("product_id", flat=True)
    )
    ordered_unique = list(dict.fromkeys(viewed_ids))[:limit]
    if not ordered_unique:
        return []
    products = {
        product.pk: product
        for product in _public_products().filter(pk__in=ordered_unique)
    }
    return [products[pk] for pk in ordered_unique if pk in products]


def recent_searches(request, limit=6):
    scope = _visitor_scope(request)
    rows = (
        SearchEvent.objects.filter(scope)
        .exclude(normalized_query="")
        .order_by("-created_at")
        .values("query", "normalized_query", "results_count", "created_at")
    )
    seen, unique = set(), []
    for row in rows:
        if row["normalized_query"] in seen:
            continue
        seen.add(row["normalized_query"])
        unique.append(row)
        if len(unique) >= limit:
            break
    return unique


def _public_products():
    return (
        Product.objects.filter(status=Product.Status.APPROVED, is_active=True)
        .select_related("category", "supplier__user")
        .prefetch_related("images")
    )


def interest_signals(request):
    """The categories and cities this visitor keeps coming back to."""
    scope = _visitor_scope(request)
    categories = list(
        ProductView.objects.filter(scope, product__category__isnull=False)
        .values("product__category")
        .annotate(hits=Count("id"))
        .order_by("-hits")
        .values_list("product__category", flat=True)[:3]
    )
    cities = list(
        ProductView.objects.filter(scope)
        .exclude(product__city="")
        .values("product__city")
        .annotate(hits=Count("id"))
        .order_by("-hits")
        .values_list("product__city", flat=True)[:2]
    )
    if request.user.is_authenticated:
        favourite_categories = list(
            Favorite.objects.filter(user=request.user, product__category__isnull=False)
            .values_list("product__category", flat=True)[:3]
        )
        categories = list(dict.fromkeys(categories + favourite_categories))
    return {"categories": categories, "cities": cities}


def recommended_products(request, limit=8):
    """Products similar to what the visitor already looked at.

    Falls back to the most viewed listings for a brand-new visitor, so the
    section is never empty.
    """
    signals = interest_signals(request)
    seen_ids = set(
        ProductView.objects.filter(_visitor_scope(request)).values_list("product_id", flat=True)
    )
    if request.user.is_authenticated:
        seen_ids |= set(
            Favorite.objects.filter(user=request.user).values_list("product_id", flat=True)
        )

    queryset = _public_products().exclude(pk__in=seen_ids)
    if request.user.is_authenticated:
        queryset = queryset.exclude(supplier__user=request.user)

    if signals["categories"]:
        preferred = queryset.filter(category__in=signals["categories"])
        if signals["cities"]:
            # Same interest *and* same city first, then widen if too few.
            local = preferred.filter(city__in=signals["cities"])
            results = list(local.order_by("-views_count")[:limit])
            if len(results) < limit:
                extra = preferred.exclude(pk__in=[p.pk for p in results])
                results += list(extra.order_by("-views_count")[: limit - len(results)])
        else:
            results = list(preferred.order_by("-views_count")[:limit])
        if len(results) >= limit:
            return results
        filler = queryset.exclude(pk__in=[p.pk for p in results]).order_by("-views_count")
        return results + list(filler[: limit - len(results)])

    return list(queryset.order_by("-views_count")[:limit])


def new_arrivals(request, limit=8):
    """Latest listings, narrowed to the visitor's interests when known."""
    signals = interest_signals(request)
    queryset = _public_products()
    if signals["categories"]:
        narrowed = queryset.filter(category__in=signals["categories"])
        if narrowed.exists():
            queryset = narrowed
    return list(queryset.order_by("-published_at", "-created_at")[:limit])
