"""URL configuration for teampulse project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("empresas/", include("empresas.urls")),
    path("organizacion/", include("organizacion.urls")),
    path("evaluaciones/", include("evaluaciones.urls")),  # WP4 plantillas + WP5 ciclos
    path("notificaciones/", include("notificaciones.urls")),
    path("reportes/", include("reportes.urls")),
    path("auditoria/", include("auditoria.urls")),
    path("", include("app.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

# WP1 — panel superadmin (alias; no reemplaza /empresas/)
urlpatterns += [
    path(
        "plataforma/empresas/",
        include(("empresas.urls", "empresas"), namespace="plataforma"),
    ),
]
