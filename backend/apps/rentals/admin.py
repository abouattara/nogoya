from django.contrib import admin

from .models import RentalRequest


@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "product", "client", "start_date", "end_date", "status",
        "supplier_checked_at", "contact_released_at", "handled_by",
    )
    list_filter = ("status", "created_at")
    search_fields = ("product__title", "client__phone", "message")
    raw_id_fields = ("product", "client", "handled_by", "released_by", "thread")
    readonly_fields = ("supplier_checked_at", "contact_released_at", "released_by")
    date_hierarchy = "created_at"
