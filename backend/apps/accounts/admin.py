from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = ("phone", "first_name", "last_name", "role", "is_phone_verified", "is_staff")
    list_filter = ("role", "is_phone_verified", "is_staff", "is_superuser")
    search_fields = ("phone", "first_name", "last_name", "email")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Identité"), {"fields": ("first_name", "last_name", "email", "gender", "birth_date", "avatar")}),
        (_("Rôle & vérification"), {"fields": ("role", "is_phone_verified")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Dates"), {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ("created_at", "last_login")
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "role", "password1", "password2"),
        }),
    )
