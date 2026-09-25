from django.contrib import admin

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
    list_display = ("title", "supplier", "listing_type", "price", "city", "status", "created_at")
    list_filter = ("status", "listing_type", "category")
    search_fields = ("title", "city", "supplier__user__phone")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    inlines = [ProductImageInline, ProductAttributeValueInline]
    date_hierarchy = "created_at"
