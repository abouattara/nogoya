"""Analytics services: view de-duplication and search logging.

Business logic lives here (not in views/serializers) so both the REST API
and any future internal callers (Celery tasks, admin actions) share it.
"""
import re

from django.core.cache import cache
from django.db.models import F

from .models import ContactEvent, ProductView, SearchEvent

VIEW_DEDUPE_TTL = 60 * 60 * 12  # a visitor re-viewing within 12h doesn't recount


def _actor_key(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"anon:{getattr(request, 'visitor_id', 'unknown')}"


def record_product_view(request, product):
    """Increment Product.views_count at most once per actor per TTL window.

    Returns True if this call counted as a new view.
    """
    actor = _actor_key(request)
    cache_key = f"pv:{product.pk}:{actor}"
    if cache.get(cache_key):
        return False
    cache.set(cache_key, 1, timeout=VIEW_DEDUPE_TTL)

    type(product).objects.filter(pk=product.pk).update(views_count=F("views_count") + 1)
    ProductView.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        visitor_id="" if request.user.is_authenticated else getattr(request, "visitor_id", ""),
    )
    return True


def record_contact_event(request, product, channel="phone"):
    return ContactEvent.objects.create(product=product, user=request.user, channel=channel)


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(query):
    return _WHITESPACE_RE.sub(" ", query or "").strip().lower()


def record_search_event(request, *, query, filters, results_count):
    normalized = normalize_query(query)
    if not normalized and not filters:
        return None  # nothing meaningful to log (empty homepage load, etc.)
    return SearchEvent.objects.create(
        user=request.user if request.user.is_authenticated else None,
        visitor_id="" if request.user.is_authenticated else getattr(request, "visitor_id", ""),
        query=query or "",
        normalized_query=normalized,
        filters=filters or {},
        results_count=results_count,
    )
