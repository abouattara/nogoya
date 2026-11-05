from django.contrib import admin

from .models import TermsAcceptance


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
    """En lecture seule : une acceptation se constate, elle ne se fabrique pas.

    Pouvoir en créer une à la main depuis l'administration viderait la
    trace de son sens le jour où elle servirait.
    """

    list_display = ["user", "version", "accepted_at"]
    list_filter = ["version"]
    search_fields = ["user__phone", "user__first_name", "user__last_name"]
    readonly_fields = ["user", "version", "accepted_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
