from rest_framework import viewsets
from rest_framework.response import Response

from app.api.permissions import EmpresaActivaPermission, RolPermission
from app.querysets import for_empresa
from auditoria.models import AuditLog
from auditoria.serializers import AuditLogSerializer
from cuentas.models import Usuario


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]

    def get_queryset(self):
        qs = (
            AuditLog.objects.select_related("usuario", "empresa")
            .order_by("-created_at")
        )
        qs = for_empresa(qs, getattr(self.request, "empresa", None))
        usuario = self.request.query_params.get("usuario")
        accion = self.request.query_params.get("accion")
        modelo = self.request.query_params.get("modelo")
        desde = self.request.query_params.get("fecha_desde")
        hasta = self.request.query_params.get("fecha_hasta")
        if usuario:
            qs = qs.filter(usuario_id=usuario)
        if accion:
            qs = qs.filter(accion=accion)
        if modelo:
            qs = qs.filter(modelo=modelo)
        if desde:
            qs = qs.filter(created_at__date__gte=desde)
        if hasta:
            qs = qs.filter(created_at__date__lte=hasta)
        return qs

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
        }
        return response
