from django.urls import path

from . import views

app_name = "empresas"

urlpatterns = [
    path("", views.EmpresaListaView.as_view(), name="lista"),
    path("nueva/", views.EmpresaCrearView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.EmpresaEditarView.as_view(), name="editar"),
    path("<int:pk>/suspender/", views.EmpresaSuspenderView.as_view(), name="suspender"),
    path("<int:pk>/activar/", views.EmpresaActivarView.as_view(), name="activar"),
    path("<int:pk>/seleccionar/", views.EmpresaSeleccionarView.as_view(), name="seleccionar"),
    path("<int:pk>/", views.EmpresaDetalleView.as_view(), name="detalle"),
]
