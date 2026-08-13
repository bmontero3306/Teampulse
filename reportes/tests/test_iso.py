from io import BytesIO

from django.test import TestCase
from django.urls import reverse

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


class IsoPermisosTests(TestCase):
    def setUp(self):
        self.datos = escenario_iso_basico()
        self.urls = [
            reverse("reportes:iso"),
            reverse("reportes:iso_pdf"),
            reverse("reportes:iso_excel"),
        ]

    def test_empleado_recibe_403(self):
        self.client.force_login(self.datos["empleado"])
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_supervisor_recibe_403(self):
        self.client.force_login(self.datos["supervisor"])
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(reverse("reportes:iso"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_admin_rrhh_ve_preview(self):
        self.client.force_login(self.datos["admin"])
        response = self.client.get(reverse("reportes:iso"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reportes ISO 9001")
        self.assertContains(response, self.datos["empleado"].first_name)
        self.assertContains(response, "Exportar PDF")
        self.assertContains(response, "Exportar Excel")


class IsoExportTests(TestCase):
    def setUp(self):
        self.datos = escenario_iso_basico()
        self.client.force_login(self.datos["admin"])

    def test_export_pdf_200_y_content_type(self):
        response = self.client.get(reverse("reportes:iso_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_PDF)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_export_excel_200_y_content_type(self):
        response = self.client.get(reverse("reportes:iso_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_EXCEL)
        self.assertIn("spreadsheet", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn(".xlsx", response["Content-Disposition"])

    def test_excel_tiene_hoja_resumen_y_detalle(self):
        from openpyxl import load_workbook

        response = self.client.get(reverse("reportes:iso_excel"))
        wb = load_workbook(BytesIO(response.content))
        self.assertEqual(wb.sheetnames, ["Resumen", "Detalle"])
        self.assertIn("ISO 9001", wb["Resumen"]["A1"].value)
        headers = [cell.value for cell in wb["Detalle"][1]]
        self.assertIn("Evaluado", headers)
        self.assertIn("Hash de firma", headers)

    def test_export_registra_auditoria(self):
        self.client.get(reverse("reportes:iso_pdf"))
        self.client.get(reverse("reportes:iso_excel"))
        logs = AuditLog.objects.filter(accion=Accion.EXPORTAR, empresa=self.datos["empresa"])
        self.assertEqual(logs.count(), 2)
        formatos = {log.payload.get("formato") for log in logs}
        self.assertEqual(formatos, {"pdf", "excel"})


class IsoFiltroTenantTests(TestCase):
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

    def test_filtro_de_area_no_filtra_otra_empresa(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a, "area": self.area_b})
        pks = set(qs.values_list("pk", flat=True))
        self.assertNotIn(self.eval_b.pk, pks)
        self.assertFalse(qs.filter(empresa=self.empresa_b).exists())

        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("reportes:iso"), {"area": self.area_b.pk})
        self.assertEqual(response.status_code, 200)
        pks_vista = {ev.pk for ev in response.context["evaluaciones"]}
        self.assertNotIn(self.eval_b.pk, pks_vista)
        self.assertTrue(all(ev.empresa_id == self.empresa_a.pk for ev in response.context["evaluaciones"]))
        self.assertNotContains(response, "Nestor")

    def test_queryset_siempre_por_empresa(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a})
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.eval_a.pk, pks)
        self.assertNotIn(self.eval_b.pk, pks)

    def test_filtro_area_propia(self):
        qs = generar_iso_queryset({"empresa": self.empresa_a, "area": self.area_a})
        self.assertEqual(list(qs.values_list("pk", flat=True)), [self.eval_a.pk])


class IsoIndicadoresTests(TestCase):
    def test_porcentajes_y_totales(self):
        datos = escenario_iso_basico()
        reporte = construir_iso_reporte({"empresa": datos["empresa"], "ciclo": datos["ciclo"]})
        self.assertEqual(reporte.indicadores.total, 2)
        self.assertEqual(reporte.indicadores.firmadas, 1)
        self.assertEqual(reporte.indicadores.pct_firmadas, 50.0)
        self.assertEqual(reporte.indicadores.auto_completas, 1)
        self.assertIsNotNone(reporte.indicadores.promedio_auto)
        self.assertIsNotNone(reporte.indicadores.promedio_firma)
