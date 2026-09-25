from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SupplierProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_supplier_profile(sender, instance, **kwargs):
    """Create the supplier profile as soon as a user carries the supplier role.

    Covers registration, admin creation, and later role upgrades. Idempotent.
    """
    if getattr(instance, "role", None) == instance.Role.SUPPLIER:
        SupplierProfile.objects.get_or_create(user=instance)
