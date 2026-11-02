"""Traiter les demandes depuis l'administration.

L'écran dédié viendra ; en attendant, les trois gestes du parcours sont ici
sous forme d'actions. Ce ne sont pas des champs libres : horodater soi-même
une vérification qu'on n'a pas faite viderait `supplier_checked_at` de son
sens, et c'est ce champ qui distingue « le fournisseur a confirmé » de
« quelqu'un a supposé ».
"""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import RentalRequest


@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "product_link", "client", "period", "status",
        "checked", "released", "handled_by",
    )
    list_filter = ("status", "created_at")
    search_fields = ("product__title", "client__phone", "message", "staff_note")
    raw_id_fields = ("product", "client", "handled_by", "released_by", "thread")
    readonly_fields = (
        "product", "client", "start_date", "end_date", "message",
        "supplier_checked_at", "contact_released_at", "released_by", "thread",
    )
    date_hierarchy = "created_at"
    actions = ["mark_available", "mark_unavailable", "release_contact"]

    @admin.display(description="Bien")
    def product_link(self, obj):
        return format_html(
            '<a href="/admin/catalog/product/{}/change/">{}</a>', obj.product_id, obj.product.title
        )

    @admin.display(description="Période")
    def period(self, obj):
        return f"{obj.start_date:%d/%m} → {obj.end_date:%d/%m} ({obj.nights} j)"

    @admin.display(description="Vérifié", boolean=True)
    def checked(self, obj):
        return obj.supplier_checked_at is not None

    @admin.display(description="Transmis", boolean=True)
    def released(self, obj):
        return obj.contact_released_at is not None

    @admin.action(description="Disponible — le fournisseur a confirmé")
    def mark_available(self, request, queryset):
        updated = 0
        for demande in queryset:
            demande.status = RentalRequest.Status.AVAILABLE
            demande.supplier_checked_at = timezone.now()
            demande.handled_by = demande.handled_by or request.user
            demande.save(
                update_fields=["status", "supplier_checked_at", "handled_by", "updated_at"]
            )
            updated += 1
        self.message_user(request, f"{updated} demande(s) marquée(s) disponible(s).", messages.SUCCESS)

    @admin.action(description="Indisponible pour ces dates")
    def mark_unavailable(self, request, queryset):
        updated = 0
        for demande in queryset:
            demande.status = RentalRequest.Status.UNAVAILABLE
            demande.supplier_checked_at = timezone.now()
            demande.handled_by = demande.handled_by or request.user
            demande.save(
                update_fields=["status", "supplier_checked_at", "handled_by", "updated_at"]
            )
            updated += 1
        self.message_user(request, f"{updated} demande(s) marquée(s) indisponible(s).", messages.SUCCESS)

    @admin.action(description="Transmettre les coordonnées au client")
    def release_contact(self, request, queryset):
        released, blocked = 0, []
        for demande in queryset:
            if demande.supplier_checked_at is None:
                blocked.append(f"#{demande.pk} : disponibilité non vérifiée.")
                continue
            if demande.status == RentalRequest.Status.UNAVAILABLE:
                blocked.append(f"#{demande.pk} : bien déclaré indisponible.")
                continue
            demande.contact_released_at = demande.contact_released_at or timezone.now()
            demande.released_by = demande.released_by or request.user
            demande.status = RentalRequest.Status.CONNECTED
            demande.handled_by = demande.handled_by or request.user
            demande.save(
                update_fields=[
                    "contact_released_at", "released_by", "status", "handled_by", "updated_at",
                ]
            )
            released += 1
        if released:
            self.message_user(request, f"Coordonnées transmises pour {released} demande(s).", messages.SUCCESS)
        for problem in blocked:
            # Mettre en relation sur un bien indisponible est la seule faute
            # que ce schéma existe pour éviter : on le dit, on ne le fait pas.
            self.message_user(request, problem, messages.WARNING)

    def has_add_permission(self, request):
        # Une demande vient d'un client, elle ne se saisit pas.
        return False
