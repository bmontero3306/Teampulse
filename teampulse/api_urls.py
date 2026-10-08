from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.api.views import AyudaIndexView, AyudaPaginaView, DashboardView
from auditoria.api.views import AuditLogViewSet
from cuentas.api.views import (
    CambioClaveView,
    LoginView,
    LogoutView,
    MeView,
    ResetConfirmarView,
    ResetSolicitudView,
    UsuarioViewSet,
)
from empresas.api.views import EmpresaViewSet
from evaluaciones.api.views import (
    CicloViewSet,
    EvaluacionViewSet,
    PlantillaViewSet,
    ResultadoPdfView,
)
from notificaciones.api.views import NotificacionViewSet
from organizacion.api.views import (
    AreaViewSet,
    CompetenciaViewSet,
    OrganigramaView,
    PuestoViewSet,
)
from reportes.api.views import IsoExcelApiView, IsoPdfApiView, IsoPreviewApiView

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuarios")
router.register("empresas", EmpresaViewSet, basename="empresas")
router.register("areas", AreaViewSet, basename="areas")
router.register("puestos", PuestoViewSet, basename="puestos")
router.register("competencias", CompetenciaViewSet, basename="competencias")
router.register("organigrama", OrganigramaView, basename="organigrama")
router.register("plantillas", PlantillaViewSet, basename="plantillas")
router.register("ciclos", CicloViewSet, basename="ciclos")
router.register("evaluaciones", EvaluacionViewSet, basename="evaluaciones")
router.register("notificaciones", NotificacionViewSet, basename="notificaciones")
router.register("auditoria", AuditLogViewSet, basename="auditoria")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("auth/me/", MeView.as_view(), name="api-me"),
    path("auth/password/change/", CambioClaveView.as_view(), name="api-password-change"),
    path("auth/password/reset/", ResetSolicitudView.as_view(), name="api-password-reset"),
    path(
        "auth/password/reset/confirm/",
        ResetConfirmarView.as_view(),
        name="api-password-reset-confirm",
    ),
    path("dashboard/", DashboardView.as_view(), name="api-dashboard"),
    path("ayuda/", AyudaIndexView.as_view(), name="api-ayuda"),
    path("ayuda/<slug:slug>/", AyudaPaginaView.as_view(), name="api-ayuda-pagina"),
    path("reportes/iso/", IsoPreviewApiView.as_view(), name="api-iso"),
    path("reportes/iso/pdf/", IsoPdfApiView.as_view(), name="api-iso-pdf"),
    path("reportes/iso/excel/", IsoExcelApiView.as_view(), name="api-iso-excel"),
    path(
        "evaluaciones/<int:pk>/resultado.pdf",
        ResultadoPdfView.as_view(),
        name="api-resultado-pdf",
    ),
    path("", include(router.urls)),
]
