from django.urls import path

from . import views

app_name = "organizacion"

urlpatterns = [
    path("organigrama/", views.OrganigramaView.as_view(), name="organigrama"),
    path("puestos/", views.PuestoListView.as_view(), name="puestos"),
    path("puestos/nuevo/", views.PuestoFormView.as_view(), name="puesto_crear"),
    path(
        "puestos/<int:pk>/editar/",
        views.PuestoFormView.as_view(),
        name="puesto_editar",
    ),
    path("areas/", views.AreaListView.as_view(), name="areas"),
    path("areas/nueva/", views.AreaFormView.as_view(), name="area_form"),
    path("areas/<int:pk>/editar/", views.AreaFormView.as_view(), name="area_form"),
    path("competencias/", views.CompetenciaListView.as_view(), name="competencias"),
    path(
        "competencias/nueva/",
        views.CompetenciaFormView.as_view(),
        name="competencia_form",
    ),
    path(
        "competencias/<int:pk>/editar/",
        views.CompetenciaFormView.as_view(),
        name="competencia_form",
    ),
]
