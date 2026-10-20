"""L'écran où un humain décide.

Tout le pipeline s'arrête ici : rien n'est publié sans qu'une personne ait
regardé l'annonce, vérifié le lien d'origine et cliqué. Cet écran doit donc
rendre ce geste rapide — prévisualiser, corriger, publier ou rejeter en
série — sans jamais le rendre machinal.
"""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from apps.catalog.models import Product

from .models import ListingImport, ListingSource
from .services import run_import


@admin.register(ListingSource)
class ListingSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name", "kind", "is_active", "allows_image_reuse",
        "last_run_at", "last_run_status", "imports_count",
    )
    list_filter = ("kind", "is_active", "last_run_status", "allows_image_reuse")
    search_fields = ("name", "slug", "reference_url", "endpoint")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("last_run_at", "last_run_status", "last_run_report",
                       "authorization_confirmed_by", "authorization_confirmed_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "kind", "reference_url", "endpoint")}),
        ("Autorisation", {
            "description": (
                "Une source ne peut pas être activée sans que l'autorisation soit décrite. "
                "Importer une annonce, c'est reprendre le travail de quelqu'un : la seule "
                "question qui compte est de savoir si on en a le droit."
            ),
            "fields": ("is_active", "authorization_note", "allows_image_reuse",
                       "allows_contact_details", "authorization_confirmed_by",
                       "authorization_confirmed_at"),
        }),
        ("Configuration technique", {
            "fields": ("config", "credential_env_var", "request_delay_seconds",
                       "min_interval_minutes", "max_items_per_run"),
        }),
        ("Dernière exécution", {"fields": ("last_run_at", "last_run_status", "last_run_report")}),
    )
    actions = ["run_now", "run_dry"]

    @admin.display(description="Imports")
    def imports_count(self, obj):
        return obj.imports.count()

    def save_model(self, request, obj, form, change):
        # Qui a validé l'autorisation, et quand : une activation doit être
        # imputable à quelqu'un.
        if obj.is_active and not obj.authorization_confirmed_at:
            obj.authorization_confirmed_by = request.user
            obj.authorization_confirmed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="Lancer l'import maintenant")
    def run_now(self, request, queryset):
        self._run(request, queryset, dry_run=False)

    @admin.action(description="Simuler l'import (n'écrit rien)")
    def run_dry(self, request, queryset):
        self._run(request, queryset, dry_run=True)

    def _run(self, request, queryset, *, dry_run):
        for source in queryset:
            report = run_import(source, dry_run=dry_run)
            level = messages.SUCCESS
            if report.status == ListingSource.RunStatus.FAILED:
                level = messages.ERROR
            elif report.status == ListingSource.RunStatus.PARTIAL:
                level = messages.WARNING
            self.message_user(request, report.summary(), level=level)


@admin.register(ListingImport)
class ListingImportAdmin(admin.ModelAdmin):
    list_display = (
        "title_display", "source", "status", "city_display", "price_display",
        "product_status", "collected_at", "original_link",
    )
    list_filter = ("status", "source", "collected_at")
    search_fields = ("external_id", "original_url", "normalized__title", "error_message")
    readonly_fields = (
        "source", "external_id", "fingerprint", "normalized", "raw_payload",
        "collected_at", "last_checked_at", "duplicate_of", "original_link",
    )
    raw_id_fields = ("product",)
    date_hierarchy = "collected_at"
    actions = ["publish_products", "reject_products", "mark_unavailable"]

    @admin.display(description="Titre", ordering="normalized__title")
    def title_display(self, obj):
        return obj.normalized.get("title") or obj.external_id or "—"

    @admin.display(description="Ville")
    def city_display(self, obj):
        return obj.normalized.get("city") or "—"

    @admin.display(description="Prix")
    def price_display(self, obj):
        price = obj.normalized.get("price")
        return f"{price} {obj.normalized.get('currency') or ''}".strip() if price else "—"

    @admin.display(description="Annonce")
    def product_status(self, obj):
        if not obj.product_id:
            return "—"
        return obj.product.get_status_display()

    @admin.display(description="Source")
    def original_link(self, obj):
        if not obj.original_url:
            return "—"
        # `format_html` échappe l'URL : elle vient d'un tiers.
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer nofollow">Voir l\'annonce</a>',
            obj.original_url,
        )

    @admin.action(description="Publier l'annonce liée")
    def publish_products(self, request, queryset):
        published = 0
        blocked = []
        for record in queryset.select_related("product"):
            product = record.product
            if product is None:
                blocked.append(f"{record} : aucune annonce créée.")
                continue
            if not product.title or product.price is None or not product.city:
                blocked.append(f"{product.title or record} : informations incomplètes.")
                continue
            product.status = Product.Status.APPROVED
            product.is_active = True
            product.published_at = product.published_at or timezone.now()
            product.save(update_fields=["status", "is_active", "published_at", "updated_at"])
            published += 1
        if published:
            self.message_user(request, f"{published} annonce(s) publiée(s).", messages.SUCCESS)
        for problem in blocked:
            self.message_user(request, problem, messages.WARNING)

    @admin.action(description="Rejeter l'annonce liée")
    def reject_products(self, request, queryset):
        self._set_status(request, queryset, Product.Status.REJECTED, "rejetée(s)")

    @admin.action(description="Marquer le bien indisponible")
    def mark_unavailable(self, request, queryset):
        self._set_status(request, queryset, Product.Status.UNAVAILABLE, "marquée(s) indisponible(s)")

    def _set_status(self, request, queryset, status, label):
        ids = [r.product_id for r in queryset if r.product_id]
        updated = Product.objects.filter(pk__in=ids).update(
            status=status, is_active=False, updated_at=timezone.now()
        )
        self.message_user(request, f"{updated} annonce(s) {label}.", messages.SUCCESS)

    def has_add_permission(self, request):
        # Une ligne d'import est produite par une exécution, jamais saisie.
        return False
