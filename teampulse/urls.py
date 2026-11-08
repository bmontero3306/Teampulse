"""URL configuration for teampulse project.

Django monta el admin, la API y el catch-all de la SPA.
"""

from django.contrib import admin
from django.urls import include, path, re_path

from teampulse.spa import spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("teampulse.api_urls")),
    re_path(r"^(?P<path>.*)$", spa, name="spa"),
]
