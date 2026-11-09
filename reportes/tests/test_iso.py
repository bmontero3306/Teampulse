from datetime import timedelta
from io import BytesIO

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import (
    make_area,
    make_ciclo,
    make_empresa,
    make_evaluacion,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from auditoria.constants import Accion
from auditoria.models import AuditLog
from evaluaciones.models import Evaluacion
from reportes.services import (
    CONTENT_TYPE_EXCEL,
    CONTENT_TYPE_PDF,
    construir_iso_reporte,
    generar_iso_queryset,
)
from reportes.tests.helpers import escenario_iso_basico

URL_ISO = "/api/v1/reportes/iso/"
URL_PDF = "/api/v1/reportes/iso/pdf/"
URL_EXCEL = "/api/v1/reportes/iso/excel/"

CLAVES_FILA = {
    "id",
    "ciclo",
    "evaluado",
    "evaluador",
    "area",
    "puesto",
    "estado",
    "estado_display",
    "en_borrador",
    "con_observacion",
    "enviada_auto_en",
    "cerrada_supervisor_en",
    "firmada_en",
    "firma_hash",
}
CLAVES_INDICADORES = {
    "total",
    "auto_completas",
    "pct_auto",
    "supervisor",
    "pct_supervisor",
    "firmadas",
    "pct_firmadas",
    "con_observacion",
    "pct_observacion",
    "promedio_auto",
    "promedio_supervisor",
    "promedio_firma",
}


class IsoApiTestCase(APITestCase):
    def auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class IsoPermisosTests(IsoApiTestCase):
    def setUp(self):
        self.datos = escenario_iso_basico()
        self.urls = [URL_ISO, URL_PDF, URL_EXCEL]

    def test_empleado_recibe_403(self):
        self.auth(self.datos["empleado"])
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_supervisor_recibe_403(self):
        self.auth(self.datos["supervisor"])
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_anonimo_recibe_401(self):
        response = self.client.get(URL_ISO)
        self.assertEqual(response.status_code, 401)

    def test_admin_rrhh_ve_preview(self):
        self.auth(self.datos["admin"])
        response = self.client.get(URL_ISO)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["empresa"], self.datos["empresa"].nombre)
        self.assertEqual(set(response.data["indicadores"]), CLAVES_INDICADORES)
        filas = response.data["evaluaciones"]
        self.assertTrue(filas)
        self.assertEqual(set(filas[0]), CLAVES_FILA)
        nombres = {fila["evaluado"] for fila in filas}
        self.assertIn("Pablo Evaluado", nombres)
        firmada = next(fila for fila in filas if fila["id"] == self.datos["firmada"].pk)
        self.assertEqual(firmada["area"], self.datos["area"].nombre)
        self.assertEqual(firmada["ciclo"], self.datos["ciclo"].nombre)
        self.assertEqual(firmada["evaluador"], "Sara Jefa")
        self.assertEqual(firmada["estado"], Evaluacion.Estado.CERRADA)
        self.assertEqual(firmada["firma_hash"], "a" * 64)
        self.assertIsNotNone(firmada["enviada_auto_en"])
        self.assertIsNotNone(firmada["cerrada_supervisor_en"])
        self.assertIsNotNone(firmada["firmada_en"])
        self.assertEqual(response.data["opciones"]["empresas"], [])
        self.assertTrue(response.data["opciones"]["ciclos"])
        self.assertTrue(response.data["opciones"]["areas"])


class IsoExportTests(IsoApiTestCase):
    def setUp(self):
        self.datos = escenario_iso_basico()
        self.auth(self.datos["admin"])

    def test_export_pdf_200_y_content_type(self):
        response = self.client.get(URL_PDF)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_PDF)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_export_excel_200_y_content_type(self):
        response = self.client.get(URL_EXCEL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_EXCEL)
        self.assertIn("spreadsheet", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn(".xlsx", response["Content-Disposition"])

    def test_excel_tiene_hoja_resumen_y_detalle(self):
        from openpyxl import load_workbook

        response = self.client.get(URL_EXCEL)
        wb = load_workbook(BytesIO(response.content))
        self.assertEqual(wb.sheetnames, ["Resumen", "Detalle"])
        self.assertIn("ISO 9001", wb["Resumen"]["A1"].value)
        headers = [cell.value for cell in wb["Detalle"][1]]
        self.assertIn("Evaluado", headers)
        self.assertIn("Hash de firma", headers)

    def test_export_registra_auditoria(self):
        self.client.get(URL_PDF)
        self.client.get(URL_EXCEL)
        logs = AuditLog.objects.filter(accion=Accion.EXPORTAR, empresa=self.datos["empresa"])
        self.assertEqual(logs.count(), 2)
        formatos = {log.payload.get("formato") for log in logs}
        self.assertEqual(formatos, {"pdf", "excel"})


class IsoFiltroTenantTests(IsoApiTestCase):
    def setUp(self):
        self.empresa_a = make_empresa()
        self.empresa_b = make_empresa()
        self.area_a = make_area(self.empresa_a, nombre="Área A")
        self.area_b = make_area(self.empresa_b, nombre="Área B")
        puesto_a = make_puesto(self.empresa_a, area=self.area_a)
        puesto_b = make_puesto(self.empresa_b, area=self.area_b)
        plantilla_a = make_plantilla(self.empresa_a)
        plantilla_b = make_plantilla(self.empresa_b)
        self.ciclo_a = make_ciclo(self.empresa_a, plantilla_default=plantilla_a)
        self.ciclo_b = make_ciclo(self.empresa_b, plantilla_default=plantilla_b)
        self.admin_a = make_usuario(self.empresa_a, rol="admin_rrhh")
        empleado_a = make_usuario(
            self.empresa_a,
            rol="empleado",
            puesto=puesto_a,
            area=self.area_a,
            first_name="Lucia",
            last_name="DeA",
        )
        empleado_b = make_usuario(
            self.empresa_b,
            rol="empleado",
            puesto=puesto_b,
            area=self.area_b,
            first_name="Nestor",
            last_name="DeB",
        )
        self.eval_a = make_evaluacion(
            self.ciclo_a, empleado_a, puesto=puesto_a, estado=Evaluacion.Estado.CERRADA
        )
        self.eval_b = make_evaluacion(
            self.ciclo_b, empleado_b, puesto=puesto_b, estado=Evaluacion.Estado.CERRADA
        )

    def _ids(self, response):
        return {fila["id"] for fila in response.data["evaluaciones"]}

    def test_filtro_de_area_no_filtra_otra_empresa(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a, "area": self.area_b})
        pks = set(qs.values_list("pk", flat=True))
        self.assertNotIn(self.eval_b.pk, pks)
        self.assertFalse(qs.filter(empresa=self.empresa_b).exists())

        self.auth(self.admin_a)
        response = self.client.get(URL_ISO, {"area": self.area_b.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.eval_b.pk, self._ids(response))
        self.assertIn(self.eval_a.pk, self._ids(response))
        nombres = {fila["evaluado"] for fila in response.data["evaluaciones"]}
        self.assertNotIn("Nestor DeB", nombres)
        self.assertEqual(response.data["empresa"], self.empresa_a.nombre)

    def test_admin_no_cambia_de_empresa(self):
        self.auth(self.admin_a)
        response = self.client.get(URL_ISO, {"empresa": self.empresa_b.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["empresa"], self.empresa_a.nombre)
        self.assertIn(self.eval_a.pk, self._ids(response))
        self.assertNotIn(self.eval_b.pk, self._ids(response))

    def test_superadmin_elige_empresa(self):
        superadmin = make_usuario(None, rol="superadmin")
        self.auth(superadmin)
        response = self.client.get(URL_ISO, {"empresa": self.empresa_b.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["empresa"], self.empresa_b.nombre)
        self.assertEqual(self._ids(response), {self.eval_b.pk})
        self.assertTrue(response.data["opciones"]["empresas"])

    def test_queryset_siempre_por_empresa(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a})
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.eval_a.pk, pks)
        self.assertNotIn(self.eval_b.pk, pks)

    def test_filtro_area_propia(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a, "area": self.area_a})
        self.assertEqual(list(qs.values_list("pk", flat=True)), [self.eval_a.pk])

        self.auth(self.admin_a)
        response = self.client.get(URL_ISO, {"area": self.area_a.pk})
        self.assertEqual(self._ids(response), {self.eval_a.pk})

    def test_filtro_ciclo_y_estado(self):
        self.auth(self.admin_a)
        por_ciclo = self.client.get(URL_ISO, {"ciclo": self.ciclo_a.pk})
        self.assertEqual(self._ids(por_ciclo), {self.eval_a.pk})
        firmadas = self.client.get(URL_ISO, {"estado": Evaluacion.Estado.CERRADA})
        self.assertEqual(self._ids(firmadas), {self.eval_a.pk})
        sin_firmar = self.client.get(URL_ISO, {"estado": "no_firmada"})
        self.assertNotIn(self.eval_a.pk, self._ids(sin_firmar))

    def test_filtro_con_observacion(self):
        datos = escenario_iso_basico()
        firmada = datos["firmada"]
        firmada.comentario_empleado_cierre = "No coincido"
        firmada.save(update_fields=["comentario_empleado_cierre"])
        reporte = construir_iso_reporte(
            {"empresa": datos["empresa"], "estado": "con_observacion"}
        )
        self.assertEqual(list(reporte.queryset.values_list("pk", flat=True)), [firmada.pk])
        self.assertEqual(reporte.indicadores.con_observacion, 1)
        conforme = construir_iso_reporte(
            {"empresa": datos["empresa"], "estado": Evaluacion.Estado.CERRADA}
        )
        self.assertNotIn(firmada.pk, set(conforme.queryset.values_list("pk", flat=True)))

    def test_fecha_invalida_no_aplica_filtros(self):
        self.auth(self.admin_a)
        response = self.client.get(URL_ISO, {"fecha_desde": "no-es-fecha", "ciclo": self.ciclo_a.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.eval_a.pk, self._ids(response))


class IsoIndicadoresTests(IsoApiTestCase):
    def test_porcentajes_y_totales(self):
        datos = escenario_iso_basico()
        reporte = construir_iso_reporte({"empresa": datos["empresa"], "ciclo": datos["ciclo"]})
        self.assertEqual(reporte.indicadores.total, 2)
        self.assertEqual(reporte.indicadores.firmadas, 1)
        self.assertEqual(reporte.indicadores.pct_firmadas, 50.0)
        self.assertEqual(reporte.indicadores.auto_completas, 1)
        self.assertIsNotNone(reporte.indicadores.promedio_auto)
        self.assertIsNotNone(reporte.indicadores.promedio_firma)

    def test_preview_api_repite_indicadores(self):
        datos = escenario_iso_basico()
        self.auth(datos["admin"])
        response = self.client.get(URL_ISO, {"ciclo": datos["ciclo"].pk})
        self.assertEqual(response.status_code, 200)
        ind = response.data["indicadores"]
        self.assertEqual(ind["total"], 2)
        self.assertEqual(ind["firmadas"], 1)
        self.assertEqual(ind["pct_firmadas"], 50.0)
        self.assertEqual(len(response.data["evaluaciones"]), 2)

    def test_fecha_acota_el_periodo(self):
        datos = escenario_iso_basico()
        self.auth(datos["admin"])
        fuera = (timezone.localdate() + timedelta(days=400)).isoformat()
        response = self.client.get(URL_ISO, {"fecha_desde": fuera})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["evaluaciones"], [])
        self.assertEqual(response.data["indicadores"]["total"], 0)
