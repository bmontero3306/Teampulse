from rest_framework import viewsets

from app.api.permissions import EmpresaActivaPermission, RolPermission
from app.querysets import for_empresa
from auditoria.models import AuditLog
from auditoria.serializers import AuditLogQuerySerializer, AuditLogSerializer
from cuentas.models import Usuario


FILTROS = ("usuario", "accion", "modelo", "fecha_desde", "fecha_hasta")


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]

    def get_queryset(self):
        empresa = getattr(self.request, "empresa", None)
        qs = (
            AuditLog.objects.select_related("usuario", "empresa")
            .order_by("-created_at")
        )
        qs = for_empresa(qs, empresa)
        datos = self._filtros(empresa)
        if datos.get("usuario"):
            qs = qs.filter(usuario=datos["usuario"])
        if datos.get("accion"):
            qs = qs.filter(accion=datos["accion"])
        if datos.get("modelo"):
            qs = qs.filter(modelo=datos["modelo"])
        if datos.get("fecha_desde"):
            qs = qs.filter(created_at__date__gte=datos["fecha_desde"])
        if datos.get("fecha_hasta"):
            qs = qs.filter(created_at__date__lte=datos["fecha_hasta"])
        return qs

    def _filtros(self, empresa):
        cache = getattr(self, "_filtros_cache", None)
        if cache is not None:
            return cache
        params = {}
        for clave in FILTROS:
            valor = self.request.query_params.get(clave, "")
            if valor != "":
                params[clave] = valor
        usuarios = Usuario.objects.for_empresa(empresa).order_by("email")
        serializer = AuditLogQuerySerializer(data=params, usuarios=usuarios)
        serializer.is_valid(raise_exception=True)
        self._filtros_cache = serializer.validated_data
        return self._filtros_cache

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        base = for_empresa(AuditLog.objects.all(), getattr(request, "empresa", None))
        response.data = {
            "pagina": response.data,
            "acciones": list(
                base.exclude(accion="").values_list("accion", flat=True).distinct().order_by("accion")
            ),
            "modelos": list(
                base.exclude(modelo="").values_list("modelo", flat=True).distinct().order_by("modelo")
            ),
            "usuarios": list(
                Usuario.objects.for_empresa(getattr(request, "empresa", None))
                .order_by("email")
                .values("id", "email")
            ),
        }
        return response
