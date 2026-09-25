"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health checks only: the user interface is the Next.js frontend, this
    # project serves JSON (the former server-rendered pages were removed
    # once the frontend reached parity).
    path("", include("apps.core.urls")),
    path("api/v1/", include(("apps.api.urls", "api"), namespace="api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
