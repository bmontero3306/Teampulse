from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.permissions import RolPermission
from auditoria.constants import Accion
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from evaluaciones.models import CicloEvaluacion, Evaluacion
from organizacion.models import Area
from reportes.forms import IsoFiltroForm
from reportes.services import (
    CONTENT_TYPE_EXCEL,
    CONTENT_TYPE_PDF,
    construir_iso_reporte,
    exportar_iso_excel,
    exportar_iso_pdf,
    payload_auditoria_export,
)


def _filtros_api(request):
    form = IsoFiltroForm(
        request.query_params or None,
        empresa=getattr(request, "empresa", None),
        usuario=request.user,
    )
    empresa = getattr(request, "empresa", None)
    datos = form.cleaned_data if form.is_valid() else {}
    if request.user.rol == Usuario.Rol.SUPERADMIN:
        empresa = datos.get("empresa") or empresa
    return {
        "empresa": empresa,
        "ciclo": datos.get("ciclo"),
        "area": datos.get("area"),
        "estado": datos.get("estado") or "",
        "fecha_desde": datos.get("fecha_desde"),
        "fecha_hasta": datos.get("fecha_hasta"),
    }


def _iso_json(reporte):
    ind = reporte.indicadores
    filas = []
    for ev in reporte.queryset:
        filas.append(
            {
                "id": ev.pk,
                "ciclo": ev.ciclo.nombre,
                "evaluado": ev.evaluado.get_full_name() or ev.evaluado.email,
                "evaluador": (
                    ev.evaluador.get_full_name() or ev.evaluador.email if ev.evaluador_id else None
                ),
                "area": ev.puesto.area.nombre if ev.puesto_id and ev.puesto.area_id else None,
                "puesto": ev.puesto.nombre if ev.puesto_id else None,
                "estado": ev.estado,
                "estado_display": ev.get_estado_display(),
            }
        )
    return {
        "empresa": reporte.empresa.nombre if reporte.empresa else None,
        "periodo_desde": reporte.periodo_desde,
        "periodo_hasta": reporte.periodo_hasta,
        "indicadores": {
            "total": ind.total,
            "auto_completas": ind.auto_completas,
            "pct_auto": ind.pct_auto,
            "supervisor": ind.supervisor,
            "pct_supervisor": ind.pct_supervisor,
            "firmadas": ind.firmadas,
            "pct_firmadas": ind.pct_firmadas,
            "con_observacion": ind.con_observacion,
            "pct_observacion": ind.pct_observacion,
            "promedio_auto": ind.promedio_auto_txt,
            "promedio_supervisor": ind.promedio_supervisor_txt,
            "promedio_firma": ind.promedio_firma_txt,
        },
        "evaluaciones": filas,
    }


class IsoPreviewApiView(APIView):
    permission_classes = [RolPermission]
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]

    def get(self, request):
        empresa = getattr(request, "empresa", None)
        if request.user.rol != Usuario.Rol.SUPERADMIN and empresa is None:
            return Response(
                {"detail": "No hay una empresa activa en el contexto."},
                status=403,
            )
        reporte = construir_iso_reporte(_filtros_api(request))
        data = _iso_json(reporte)
        data["opciones"] = _opciones(request, reporte.empresa or empresa)
        return Response(data)


class IsoExportApiView(APIView):
    permission_classes = [RolPermission]
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]
    formato = ""

    def get(self, request):
        reporte = construir_iso_reporte(_filtros_api(request))
        if self.formato == "pdf":
            contenido = exportar_iso_pdf(reporte, usuario=request.user)
            content_type = CONTENT_TYPE_PDF
            filename = "reporte-iso.pdf"
        else:
            contenido = exportar_iso_excel(reporte, usuario=request.user)
            content_type = CONTENT_TYPE_EXCEL
            filename = "reporte-iso.xlsx"
        registrar_auditoria(
            request,
            Accion.EXPORTAR,
            instance=reporte.empresa,
            payload=payload_auditoria_export(reporte, self.formato),
        )
        response = HttpResponse(contenido, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _opciones(request, empresa):
    user = request.user
    empresas = []
    if user.rol == Usuario.Rol.SUPERADMIN:
        from empresas.models import Empresa

        empresas = list(Empresa.objects.order_by("nombre").values("id", "nombre"))
    ciclos = []
    areas = []
    if empresa is not None:
        ciclos = list(
            CicloEvaluacion.objects.for_empresa(empresa)
            .order_by("-fecha_inicio", "nombre")
            .values("id", "nombre", "estado")
        )
        areas = list(Area.objects.filter(empresa=empresa, activa=True).order_by("nombre").values("id", "nombre"))
    return {
        "empresas": empresas,
        "ciclos": ciclos,
        "areas": areas,
        "estados": [
            {"value": valor, "label": etiqueta}
            for valor, etiqueta in Evaluacion.Estado.choices
        ],
    }


class IsoPdfApiView(IsoExportApiView):
    formato = "pdf"


class IsoExcelApiView(IsoExportApiView):
    formato = "excel"
