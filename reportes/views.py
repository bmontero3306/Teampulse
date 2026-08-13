"""Vistas de reportes ISO 9001 (CU06 / WP7)."""

from django.http import HttpResponse
from django.views.generic import TemplateView, View

from app.mixins import RolRequiredMixin
from auditoria.constants import Accion
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from reportes.forms import IsoFiltroForm
from reportes.services import (
    CONTENT_TYPE_EXCEL,
    CONTENT_TYPE_PDF,
    construir_iso_reporte,
    exportar_iso_excel,
    exportar_iso_pdf,
    payload_auditoria_export,
)


class IsoReporteMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]

    def get_filtro_form(self):
        if not hasattr(self, "_filtro_form"):
            self._filtro_form = IsoFiltroForm(
                self.request.GET or None,
                empresa=getattr(self.request, "empresa", None),
                usuario=self.request.user,
            )
        return self._filtro_form

    def get_filtros(self):
        form = self.get_filtro_form()
        empresa = getattr(self.request, "empresa", None)
        datos = {}
        if form.is_bound:
            if form.is_valid():
                datos = form.cleaned_data
            else:
                datos = {}
        if self.request.user.rol == Usuario.Rol.SUPERADMIN:
            empresa = datos.get("empresa") or empresa
        filtros = {
            "empresa": empresa,
            "ciclo": datos.get("ciclo"),
            "area": datos.get("area"),
            "estado": datos.get("estado") or "",
            "fecha_desde": datos.get("fecha_desde"),
            "fecha_hasta": datos.get("fecha_hasta"),
        }
        return filtros

    def get_reporte(self):
        if not hasattr(self, "_reporte"):
            self._reporte = construir_iso_reporte(self.get_filtros())
        return self._reporte

    def querystring(self):
        return self.request.GET.urlencode()


class IsoPreviewView(IsoReporteMixin, TemplateView):
    template_name = "reportes/iso.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reporte = self.get_reporte()
        context["filtro_form"] = self.get_filtro_form()
        context["reporte"] = reporte
        context["indicadores"] = reporte.indicadores
        context["evaluaciones"] = reporte.queryset
        context["querystring"] = self.querystring()
        return context


class IsoExportMixin(IsoReporteMixin):
    formato = ""

    def get(self, request, *args, **kwargs):
        reporte = self.get_reporte()
        contenido, content_type, filename = self.generar_archivo(reporte)
        registrar_auditoria(
            request,
            Accion.EXPORTAR,
            instance=reporte.empresa,
            payload=payload_auditoria_export(reporte, self.formato),
        )
        response = HttpResponse(contenido, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def generar_archivo(self, reporte):
        raise NotImplementedError

    def _slug_empresa(self, reporte):
        nombre = getattr(reporte.empresa, "nombre", None) or "teampulse"
        limpio = "".join(ch if ch.isalnum() else "-" for ch in nombre).strip("-")
        return (limpio or "teampulse").lower()[:40]


class IsoPdfView(IsoExportMixin, View):
    formato = "pdf"

    def generar_archivo(self, reporte):
        contenido = exportar_iso_pdf(reporte, usuario=self.request.user)
        filename = f"reporte-iso-{self._slug_empresa(reporte)}.pdf"
        return contenido, CONTENT_TYPE_PDF, filename


class IsoExcelView(IsoExportMixin, View):
    formato = "excel"

    def generar_archivo(self, reporte):
        contenido = exportar_iso_excel(reporte, usuario=self.request.user)
        filename = f"reporte-iso-{self._slug_empresa(reporte)}.xlsx"
        return contenido, CONTENT_TYPE_EXCEL, filename
