"""Time-series aggregation for the supplier dashboard charts.

Everything is computed in PostgreSQL with a single grouped query per
series — no per-day loop, no Python-side bucketing of raw rows.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.catalog.models import Product
from apps.messaging.models import Message

from .models import ContactEvent, ProductView


def _date_range(days):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    return start, today


def _fill_series(rows, days, key="day", value="total"):
    """Turn sparse DB rows into one point per day (zeros included)."""
    start, today = _date_range(days)
    by_day = {row[key]: row[value] for row in rows}
    series = []
    current = start
    while current <= today:
        series.append({"date": current.isoformat(), "value": by_day.get(current, 0)})
        current += timedelta(days=1)
    return series


def views_series(profile, days=30):
    start, _ = _date_range(days)
    rows = (
        ProductView.objects.filter(product__supplier=profile, created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    return _fill_series(rows, days, key="day")


def contacts_series(profile, days=30):
    start, _ = _date_range(days)
    rows = (
        ContactEvent.objects.filter(product__supplier=profile, created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    return _fill_series(rows, days, key="day")


def messages_series(profile, days=30):
    """Messages *received* by the supplier (excludes their own replies)."""
    start, _ = _date_range(days)
    user = profile.user
    rows = (
        Message.objects.filter(created_at__date__gte=start)
        .filter(Q(conversation__participant_low=user) | Q(conversation__participant_high=user))
        .exclude(sender=user)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    return _fill_series(rows, days, key="day")


def products_breakdown(profile):
    counts = Product.objects.filter(supplier=profile).aggregate(
        online=Count("id", filter=Q(status=Product.Status.APPROVED, is_active=True)),
        unpublished=Count("id", filter=Q(status=Product.Status.APPROVED, is_active=False)),
        pending=Count("id", filter=Q(status=Product.Status.PENDING)),
        rejected=Count("id", filter=Q(status=Product.Status.REJECTED)),
    )
    return counts


def top_products(profile, limit=5):
    return list(
        Product.objects.filter(supplier=profile)
        .order_by("-views_count")[:limit]
        .values("id", "title", "slug", "views_count", "shares_count")
    )


def top_categories(profile, limit=5):
    return list(
        Product.objects.filter(supplier=profile, category__isnull=False)
        .values("category__name", "category__slug")
        .annotate(products=Count("id"))
        .order_by("-products")[:limit]
    )


def supplier_analytics(profile, days=30):
    return {
        "days": days,
        "views": views_series(profile, days),
        "contacts": contacts_series(profile, days),
        "messages": messages_series(profile, days),
        "products_breakdown": products_breakdown(profile),
        "top_products": top_products(profile),
        "top_categories": [
            {"name": row["category__name"], "slug": row["category__slug"], "products": row["products"]}
            for row in top_categories(profile)
        ],
    }
