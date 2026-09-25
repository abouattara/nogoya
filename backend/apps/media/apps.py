from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media"
    label = "nogoya_media"
    verbose_name = "Médias"

    def ready(self):
        from . import signals  # noqa: F401
