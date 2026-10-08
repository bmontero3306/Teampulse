from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.api.permissions import RolPermission
from cuentas.models import Usuario
from empresas.api.serializers import EmpresaSerializer
from empresas.models import Empresa
from empresas.services import activar_empresa, suspender_empresa


class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated, RolPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Empresa.objects.all().order_by("nombre")
        estado = self.request.query_params.get("estado")
        if user.rol == Usuario.Rol.SUPERADMIN:
            if estado:
                qs = qs.filter(estado=estado)
            return qs
        if user.rol == Usuario.Rol.ADMIN_RRHH and user.empresa_id:
            return qs.filter(pk=user.empresa_id)
        return qs.none()

    def get_permissions(self):
        if self.action in ("list", "create", "suspender", "activar"):
            self.roles_permitidos = [Usuario.Rol.SUPERADMIN]
        elif self.action in ("retrieve", "update", "partial_update"):
            self.roles_permitidos = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]
        else:
            self.roles_permitidos = [Usuario.Rol.SUPERADMIN]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def suspender(self, request, pk=None):
        empresa = self.get_object()
        suspender_empresa(empresa, request=request)
        return Response(self.get_serializer(empresa).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        empresa = self.get_object()
        activar_empresa(empresa, request=request)
        return Response(self.get_serializer(empresa).data)
