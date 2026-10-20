from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Category,
    CategoryAttribute,
    Favorite,
    Product,
    ProductAttributeValue,
    ProductImage,
)


class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 0
    fields = ("name", "slug", "attribute_type", "required", "filterable", "unit", "options", "position")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    inlines = [CategoryAttributeInline]


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "attribute_type", "required", "filterable", "position")
    list_filter = ("attribute_type", "required", "filterable", "category")
    search_fields = ("name", "category__name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__phone", "product__title")
    raw_id_fields = ("user", "product")


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 0
    readonly_fields = ("numeric_value",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ("width", "height")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Modération : annonces des membres **et** annonces référencées.

    Le même écran traite les deux, parce que la question est la même — ce
    bien mérite-t-il d'être montré ? — et que les séparer ferait oublier
    l'une des deux files.
    """

    list_display = (
        "title", "provenance_badge", "owner_display", "listing_type",
        "price", "city", "status", "last_checked_at", "created_at",
    )
    list_filter = ("status", "provenance", "listing_type", "category", "source", "city")
    search_fields = ("title", "city", "supplier__user__phone", "source_url")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    raw_id_fields = ("supplier", "source")
    readonly_fields = ("last_checked_at", "original_link")
    inlines = [ProductImageInline, ProductAttributeValueInline]
    date_hierarchy = "created_at"
    actions = ["approve", "reject", "mark_unavailable", "archive"]

    @admin.display(description="Provenance", ordering="provenance")
    def provenance_badge(self, obj):
        return obj.get_provenance_display()

    @admin.display(description="Responsable")
    def owner_display(self, obj):
        """Qui répond du bien : le membre, ou la source citée.

        Ne jamais afficher le compte de service comme un propriétaire :
        c'est exactement la confusion que la provenance sert à éviter.
        """
        if obj.is_externally_sourced:
            return f"Source : {obj.source.name}" if obj.source_id else "Source externe"
        user = obj.supplier.user
        return user.get_full_name() or user.phone

    @admin.display(description="Annonce d'origine")
    def original_link(self, obj):
        if not obj.source_url:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer nofollow">{}</a>',
            obj.source_url, obj.source_url,
        )

    @admin.action(description="Publier")
    def approve(self, request, queryset):
        updated = 0
        for product in queryset:
            product.status = Product.Status.APPROVED
            product.is_active = True
            product.published_at = product.published_at or timezone.now()
            product.save(update_fields=["status", "is_active", "published_at", "updated_at"])
            updated += 1
        self.message_user(request, f"{updated} annonce(s) publiée(s).", messages.SUCCESS)

    @admin.action(description="Rejeter")
    def reject(self, request, queryset):
        self._set(request, queryset, Product.Status.REJECTED, "rejetée(s)")

    @admin.action(description="Marquer indisponible")
    def mark_unavailable(self, request, queryset):
        self._set(request, queryset, Product.Status.UNAVAILABLE, "marquée(s) indisponible(s)")

    @admin.action(description="Archiver (retrait sur demande)")
    def archive(self, request, queryset):
        self._set(request, queryset, Product.Status.ARCHIVED, "archivée(s)")

    def _set(self, request, queryset, status, label):
        updated = queryset.update(status=status, is_active=False, updated_at=timezone.now())
        self.message_user(request, f"{updated} annonce(s) {label}.", messages.SUCCESS)
