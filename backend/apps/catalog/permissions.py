from rest_framework import permissions


class IsSupplier(permissions.BasePermission):
    message = "Seul un compte fournisseur peut publier une annonce."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_supplier or request.user.is_staff)
        )


class IsOwnerSupplierOrReadOnly(permissions.BasePermission):
    """Object-level: only the owning supplier (or staff) may write."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        profile = getattr(request.user, "supplier_profile", None)
        return profile is not None and obj.supplier_id == profile.pk


class IsImageOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        profile = getattr(request.user, "supplier_profile", None)
        return profile is not None and obj.product.supplier_id == profile.pk
