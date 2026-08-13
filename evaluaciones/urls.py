from django.urls import path

from . import views
from . import views_ciclos
from . import views_flujo

app_name = "evaluaciones"

urlpatterns = [
    # WP4
    path("plantillas/", views.PlantillaListView.as_view(), name="plantillas"),
    path("plantillas/nueva/", views.PlantillaFormView.as_view(), name="plantilla_crear"),
    path(
        "plantillas/<int:pk>/editar/",
        views.PlantillaFormView.as_view(),
        name="plantilla_editar",
    ),
    path(
        "plantillas/<int:pk>/duplicar/",
        views.PlantillaDuplicarView.as_view(),
        name="plantilla_duplicar",
    ),
    # WP5 — ciclos
    path("ciclos/", views_ciclos.CicloListView.as_view(), name="ciclos"),
    path("ciclos/nuevo/", views_ciclos.CicloCrearView.as_view(), name="ciclo_crear"),
    path(
        "ciclos/<int:pk>/",
        views_ciclos.CicloDetalleView.as_view(),
        name="ciclo_detalle",
    ),
    path(
        "ciclos/<int:pk>/activar/",
        views_ciclos.CicloActivarView.as_view(),
        name="ciclo_activar",
    ),
    path(
        "ciclos/<int:pk>/pausar/",
        views_ciclos.CicloPausarView.as_view(),
        name="ciclo_pausar",
    ),
    path(
        "ciclos/<int:pk>/cancelar/",
        views_ciclos.CicloCancelarView.as_view(),
        name="ciclo_cancelar",
    ),
    path(
        "ciclos/<int:pk>/reprogramar/",
        views_ciclos.CicloReprogramarView.as_view(),
        name="ciclo_reprogramar",
    ),
    # WP5 — flujo
    path("mias/", views_flujo.MisEvaluacionesView.as_view(), name="mias"),
    path("equipo/", views_flujo.EquipoView.as_view(), name="equipo"),
    path(
        "<int:pk>/autoevaluacion/",
        views_flujo.AutoevaluacionView.as_view(),
        name="auto",
    ),
    path(
        "<int:pk>/resultado/",
        views_flujo.ResultadoView.as_view(),
        name="resultado",
    ),
    path(
        "<int:pk>/firmar/",
        views_flujo.FirmarView.as_view(),
        name="firmar",
    ),
    path(
        "<int:pk>/supervisar/",
        views_flujo.SupervisarView.as_view(),
        name="supervisar",
    ),
]
