"""URL configuration for teampulse project."""

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

# WP1 — panel superadmin (alias; no reemplaza /empresas/)
urlpatterns += [
    path(
        "plataforma/empresas/",
        include(("empresas.urls", "empresas"), namespace="plataforma"),
    ),
]
