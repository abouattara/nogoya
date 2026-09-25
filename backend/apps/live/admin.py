from django.contrib import admin

from .models import LiveMessage, LiveProduct, LiveSession, LiveViewer


class LiveProductInline(admin.TabularInline):
    model = LiveProduct
    extra = 0
    raw_id_fields = ("product",)


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "host", "status", "started_at", "ended_at", "peak_viewers")
    list_filter = ("status", "provider")
    search_fields = ("title", "host__phone")
    raw_id_fields = ("host",)
    inlines = [LiveProductInline]
    date_hierarchy = "created_at"


@admin.register(LiveMessage)
class LiveMessageAdmin(admin.ModelAdmin):
    list_display = ("live", "sender", "created_at")
    raw_id_fields = ("live", "sender", "product")


admin.site.register(LiveViewer)
