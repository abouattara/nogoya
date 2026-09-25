from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("healthz/", views.health, name="health"),
    path("readyz/", views.ready, name="ready"),
]
