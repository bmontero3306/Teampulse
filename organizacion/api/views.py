from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from app.api.permissions import EmpresaActivaPermission, RolPermission
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from organizacion.api.serializers import (
    AreaSerializer,
    CompetenciaSerializer,
    PuestoSerializer,
)
from organizacion.models import Area, Competencia, Puesto
from organizacion.services import query_organigrama
from organizacion.views import (
    ROLES_CRUD,
    ROLES_LECTURA,
    _filtrar_areas_lectura,
    _filtrar_competencias_lectura,
    _filtrar_puestos_lectura,
    _puesto_usuario,
    puede_editar_organizacion,
)


def _nodo(puesto):
    return {
        "id": puesto.pk,
        "nombre": puesto.nombre,
        "area": puesto.area.nombre if puesto.area_id else None,
        "activo": puesto.activo,
        "hijos": [_nodo(hijo) for hijo in puesto.hijos_organigrama],
    }


class _OrganizacionBase(viewsets.ModelViewSet):
    permission_classes = [RolPermission, EmpresaActivaPermission]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.roles_permitidos = ROLES_LECTURA
        else:
            self.roles_permitidos = ROLES_CRUD
        return super().get_permissions()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["empresa"] = getattr(self.request, "empresa", None)
        return ctx

    def perform_destroy(self, instance):
        instance.delete()
        registrar_auditoria(self.request, accion="desactivar", instance=instance)


class AreaViewSet(_OrganizacionBase):
    serializer_class = AreaSerializer

    def get_queryset(self):
        qs = (
            Area.objects.for_empresa(self.request.empresa)
            .select_related("area_padre")
            .order_by("nombre")
        )
        if self.action in ("list", "retrieve"):
            return _filtrar_areas_lectura(qs, self.request.user)
        return qs


class PuestoViewSet(_OrganizacionBase):
    serializer_class = PuestoSerializer

    def get_queryset(self):
        qs = (
            Puesto.objects.for_empresa(self.request.empresa)
            .select_related("area", "puesto_superior")
            .order_by("nombre")
        )
        if self.action in ("list", "retrieve"):
            return _filtrar_puestos_lectura(qs, self.request.user)
        return qs


class CompetenciaViewSet(_OrganizacionBase):
    serializer_class = CompetenciaSerializer

    def get_queryset(self):
        qs = Competencia.objects.for_empresa(self.request.empresa).order_by("nombre")
        if self.action in ("list", "retrieve"):
            return _filtrar_competencias_lectura(qs, self.request.user)
        return qs

    @action(detail=False, methods=["post"], url_path="rapida")
    def rapida(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competencia = serializer.save()
        return Response(
            {"id": competencia.pk, "nombre": competencia.nombre, "tipo": competencia.tipo},
            status=201,
        )


class OrganigramaView(viewsets.ViewSet):
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = ROLES_LECTURA

    def list(self, request):
        user = request.user
        raiz = None
        if user.rol == Usuario.Rol.EMPLEADO:
            raiz = _puesto_usuario(user)
            if raiz is None:
                return Response(
                    {
                        "raices": [],
                        "sin_puesto": True,
                        "puede_editar": puede_editar_organizacion(user),
                    }
                )
        raices = query_organigrama(request.empresa, solo_activos=True, raiz=raiz)
        return Response(
            {
                "raices": [_nodo(nodo) for nodo in raices],
                "sin_puesto": False,
                "puede_editar": puede_editar_organizacion(user),
            }
        )
