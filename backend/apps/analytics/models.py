from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProductView(models.Model):
    """One de-duplicated view of a product (see services.record_product_view).

    Kept lightweight on purpose: this is the raw event log used to compute
    Product.views_count and the dashboard charts, which aggregate this
    table directly in SQL.
    """

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="view_events"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="product_views",
    )
    visitor_id = models.CharField(max_length=32, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "created_at"])]


class SearchEvent(models.Model):
    """A meaningful search made on the platform (analytics + future ranking)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="search_events",
    )
    visitor_id = models.CharField(max_length=32, blank=True, db_index=True)
    query = models.CharField(_("recherche"), max_length=255, blank=True)
    normalized_query = models.CharField(max_length=255, blank=True, db_index=True)
    filters = models.JSONField(default=dict, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class ContactEvent(models.Model):
    """A user revealed a supplier's contact details from a product page."""

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="contact_events"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact_events"
    )
    channel = models.CharField(
        max_length=12, choices=[("phone", "Téléphone"), ("whatsapp", "WhatsApp")], default="phone"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
