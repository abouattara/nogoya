"""Root REST API router — everything the Next.js frontend consumes lives at /api/v1/."""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api import LoginView, LogoutView, MeView, RegisterView
from apps.analytics.api import DiscoveryViewSet
from apps.catalog.api import (
    CategoryViewSet,
    FavoriteViewSet,
    ProductImageViewSet,
    ProductViewSet,
)
from apps.live.api import LiveSessionViewSet
from apps.messaging.api import ConversationViewSet, MessageReportView
from apps.notifications.api import NotificationViewSet
from apps.suppliers.api import SupplierViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("favorites", FavoriteViewSet, basename="favorite")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("message-reports", MessageReportView, basename="message-report")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("lives", LiveSessionViewSet, basename="live")
router.register("discovery", DiscoveryViewSet, basename="discovery")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="docs"),
    path("", include(router.urls)),
]
