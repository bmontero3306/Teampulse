"""URL configuration for teampulse project.

La UI de producto es la SPA. Las rutas HTML solo se montan al correr
`manage.py test`, porque esa suite todavía recorre las plantillas.
"""

import sys

from django.contrib import admin
from django.urls import include, path, re_path

from teampulse.spa import spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("teampulse.api_urls")),
]

if "test" in sys.argv:
    urlpatterns += [
        path("cuentas/", include("cuentas.urls")),
        path("empresas/", include("empresas.urls")),
        path("organizacion/", include("organizacion.urls")),
        path("evaluaciones/", include("evaluaciones.urls")),
        path("notificaciones/", include("notificaciones.urls")),
        path("reportes/", include("reportes.urls")),
        path("auditoria/", include("auditoria.urls")),
        path("", include("app.urls")),
        path(
            "plataforma/empresas/",
            include(("empresas.urls", "empresas"), namespace="plataforma"),
        ),
    ]

urlpatterns += [
    re_path(r"^(?P<path>.*)$", spa, name="spa"),
]
