from django.contrib import admin

from .models import SupplierProfile


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "is_verified", "rating_avg")
    list_filter = ("is_verified",)
    search_fields = ("user__phone", "user__first_name", "user__last_name", "city")
    raw_id_fields = ("user",)
