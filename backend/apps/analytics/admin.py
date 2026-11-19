"""Lire les recherches depuis l'administration.

En lecture seule : une recherche se constate, elle ne se corrige pas. Le
filtre « sans résultat » est celui qui sert le plus : ce sont les biens que
des gens cherchent et que le site n'a pas encore.
"""
from django.contrib import admin

from .models import SearchEvent


class ZeroResultFilter(admin.SimpleListFilter):
    title = "résultats"
    parameter_name = "resultats"

    def lookups(self, request, model_admin):
        return [("aucun", "Sans résultat"), ("au-moins-un", "Au moins un résultat")]

    def queryset(self, request, queryset):
        if self.value() == "aucun":
            return queryset.filter(results_count=0)
        if self.value() == "au-moins-un":
            return queryset.filter(results_count__gt=0)
        return queryset


@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "query", "criteres", "results_count", "channel", "auteur"]
    list_filter = [ZeroResultFilter, "channel", "created_at"]
    search_fields = ["normalized_query", "query"]
    date_hierarchy = "created_at"
    list_per_page = 100
    readonly_fields = [
        "created_at", "user", "visitor_id", "query", "normalized_query",
        "filters", "results_count", "channel",
    ]

    @admin.display(description="critères")
    def criteres(self, obj):
        return ", ".join(f"{k}={v}" for k, v in (obj.filters or {}).items()) or "—"

    @admin.display(description="qui")
    def auteur(self, obj):
        # Le nom public, jamais le numéro : la liste se lit à plusieurs.
        if obj.user_id:
            return obj.user.public_name("Membre")
        return f"visiteur {obj.visitor_id[:6]}" if obj.visitor_id else "visiteur"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
