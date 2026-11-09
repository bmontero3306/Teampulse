from datetime import date

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.permissions import RolPermission
from auditoria.constants import Accion
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from empresas.models import Empresa
from evaluaciones.models import CicloEvaluacion, Evaluacion
from organizacion.models import Area
from reportes.services import (
    CONFORMIDAD_CON_OBSERVACION,
    CONFORMIDAD_NO_FIRMADA,
    CONTENT_TYPE_EXCEL,
    CONTENT_TYPE_PDF,
    construir_iso_reporte,
    exportar_iso_excel,
    exportar_iso_pdf,
    payload_auditoria_export,
)

_ESTADOS_FILTRO = frozenset(
    {
        "",
        Evaluacion.Estado.PENDIENTE_REUNION,
        Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
        Evaluacion.Estado.CERRADA,
        CONFORMIDAD_CON_OBSERVACION,
        CONFORMIDAD_NO_FIRMADA,
    }
)


def _pk(valor):
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError


def _fecha(valor):
    if valor in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        raise ValueError


def _filtros_vacios(empresa):
    return {
        "empresa": empresa,
        "ciclo": None,
        "area": None,
        "estado": "",
        "fecha_desde": None,
        "fecha_hasta": None,
    }


def _filtros_api(request):
    params = request.query_params
    empresa = getattr(request, "empresa", None)
    if not params:
        return _filtros_vacios(empresa)

    try:
        if request.user.rol == Usuario.Rol.SUPERADMIN:
            pk_empresa = _pk(params.get("empresa"))
            if pk_empresa is not None:
                elegida = Empresa.objects.filter(pk=pk_empresa).first()
                if elegida is None:
                    return _filtros_vacios(empresa)
                empresa = elegida

        ciclo = None
        pk_ciclo = _pk(params.get("ciclo"))
        if pk_ciclo is not None:
            ciclo = (
                CicloEvaluacion.objects.for_empresa(empresa).filter(pk=pk_ciclo).first()
            )
            if ciclo is None:
                return _filtros_vacios(getattr(request, "empresa", None))

        area = None
        pk_area = _pk(params.get("area"))
        if pk_area is not None:
            area = Area.objects.for_empresa(empresa).filter(pk=pk_area).first()
            if area is None:
                return _filtros_vacios(getattr(request, "empresa", None))

        estado = params.get("estado") or ""
        if estado not in _ESTADOS_FILTRO:
            return _filtros_vacios(getattr(request, "empresa", None))

        fecha_desde = _fecha(params.get("fecha_desde"))
        fecha_hasta = _fecha(params.get("fecha_hasta"))
    except ValueError:
        return _filtros_vacios(getattr(request, "empresa", None))

    return {
        "empresa": empresa,
        "ciclo": ciclo,
        "area": area,
        "estado": estado,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }


def _slug_empresa(reporte):
    nombre = getattr(reporte.empresa, "nombre", None) or "teampulse"
    limpio = "".join(ch if ch.isalnum() else "-" for ch in nombre).strip("-")
    return (limpio or "teampulse").lower()[:40]


def _area_evaluacion(ev):
    if ev.evaluado_id and ev.evaluado.area_id:
        return ev.evaluado.area.nombre
    if ev.puesto_id and ev.puesto.area_id:
        return ev.puesto.area.nombre
    return None


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
                "area": _area_evaluacion(ev),
                "puesto": ev.puesto.nombre if ev.puesto_id else None,
                "estado": ev.estado,
                "estado_display": ev.etiqueta_estado,
                "en_borrador": ev.en_borrador,
                "con_observacion": ev.con_observacion,
                "enviada_auto_en": ev.enviada_auto_en,
                "cerrada_supervisor_en": ev.cerrada_supervisor_en,
                "firmada_en": ev.firmada_en,
                "firma_hash": ev.firma_hash or None,
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
        slug = _slug_empresa(reporte)
        if self.formato == "pdf":
            contenido = exportar_iso_pdf(reporte, usuario=request.user)
            content_type = CONTENT_TYPE_PDF
            filename = f"reporte-iso-{slug}.pdf"
        else:
            contenido = exportar_iso_excel(reporte, usuario=request.user)
            content_type = CONTENT_TYPE_EXCEL
            filename = f"reporte-iso-{slug}.xlsx"
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
        empresas = list(Empresa.objects.order_by("nombre").values("id", "nombre"))
    ciclos = []
    areas = []
    if empresa is not None:
        ciclos = list(
            CicloEvaluacion.objects.for_empresa(empresa)
            .order_by("-fecha_inicio", "nombre")
            .values("id", "nombre", "estado")
        )
        areas = list(
            Area.objects.filter(empresa=empresa, activa=True)
            .order_by("nombre")
            .values("id", "nombre")
        )
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
