from datetime import date, timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from app.seed import (
    DEMO_PASSWORD,
    EMAIL_EMPLEADO_1,
    EMAIL_RRHH_A,
    EMAIL_RRHH_B,
    EMAIL_SUPERVISOR,
    EMPRESA_A_CUIT,
    EMPRESA_B_CUIT,
    SUPERADMIN_EMAIL,
    seed_demo,
)
from app.tests.factories import make_competencia
from auditoria.constants import Accion
from auditoria.models import AuditLog
from cuentas.models import Usuario
from empresas.models import Empresa
from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaEvaluacion,
)
from evaluaciones.tests.test_ciclos import (
    CicloBaseTestCase,
    _formset_auto,
    _formset_sup,
)
from notificaciones.events import (
    AUTOEVALUACION_ENVIADA,
    CICLO_ACTIVADO,
    CONFORMIDAD_FIRMADA,
    EVALUACION_SUPERVISOR_CERRADA,
    RECORDATORIO_VENCIMIENTO,
    USUARIO_CREADO,
)
from notificaciones.models import Notificacion
from organizacion.models import Puesto
from reportes.services import CONTENT_TYPE_EXCEL, CONTENT_TYPE_PDF


def _login(client, email, password="clave-test-123"):
    return client.post(
        reverse("cuentas:login"),
        {"username": email, "password": password},
    )


def _logout(client):
    return client.post(reverse("cuentas:logout"))


def _formset_puesto(**extra):
    data = {
        "competencias-TOTAL_FORMS": "1",
        "competencias-INITIAL_FORMS": "0",
        "competencias-MIN_NUM_FORMS": "0",
        "competencias-MAX_NUM_FORMS": "1000",
        "competencias-0-competencia": "",
        "competencias-0-ponderacion": "",
    }
    data.update(extra)
    return data


class RecorridoFlujoAceptacionTests(CicloBaseTestCase):
    """UAT §13 puntos 1–3, 5, 8 (activar/firma/export) y 9."""

    def test_login_auto_supervisor_firma_export_audit_notif(self):
        self.client.force_login(self.admin)
        activar = self.client.post(
            reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk])
        )
        self.assertEqual(activar.status_code, 302)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_AUTO)
        _logout(self.client)

        login_emp = _login(self.client, self.empleado.email)
        self.assertEqual(login_emp.status_code, 302)
        mias = self.client.get(reverse("evaluaciones:mias"))
        self.assertEqual(mias.status_code, 200)
        self.assertContains(mias, "Ciclo Q1")
        self.assertContains(mias, "Completar")
        auto_get = self.client.get(reverse("evaluaciones:auto", args=[evaluacion.pk]))
        self.assertEqual(auto_get.status_code, 200)

        borrador = self.client.post(
            reverse("evaluaciones:auto", args=[evaluacion.pk]),
            _formset_auto(evaluacion, puntaje=3, accion="borrador"),
        )
        self.assertEqual(borrador.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_BORRADOR)

        enviar = self.client.post(
            reverse("evaluaciones:auto", args=[evaluacion.pk]),
            _formset_auto(evaluacion, puntaje=4, comentario="Listo UAT", accion="enviar"),
        )
        self.assertEqual(enviar.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_COMPLETA)
        _logout(self.client)

        login_sup = _login(self.client, self.supervisor.email)
        self.assertEqual(login_sup.status_code, 302)
        equipo = self.client.get(reverse("evaluaciones:equipo"))
        self.assertEqual(equipo.status_code, 200)
        self.assertContains(equipo, self.empleado.first_name)
        comparativo = self.client.get(
            reverse("evaluaciones:supervisar", args=[evaluacion.pk])
        )
        self.assertEqual(comparativo.status_code, 200)
        self.assertContains(comparativo, "vista comparativa")
        self.assertContains(comparativo, "4")
        cerrar = self.client.post(
            reverse("evaluaciones:supervisar", args=[evaluacion.pk]),
            _formset_sup(evaluacion, puntaje=5, feedback="Feedback UAT", accion="cerrar"),
        )
        self.assertEqual(cerrar.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)
        _logout(self.client)

        _login(self.client, self.empleado.email)
        resultado = self.client.get(
            reverse("evaluaciones:resultado", args=[evaluacion.pk])
        )
        self.assertEqual(resultado.status_code, 200)
        self.assertContains(resultado, "Feedback UAT")
        firmar = self.client.post(
            reverse("evaluaciones:firmar", args=[evaluacion.pk]),
            {"accion": "conformidad"},
        )
        self.assertEqual(firmar.status_code, 302)
        comprobante = self.client.get(
            reverse("evaluaciones:resultado", args=[evaluacion.pk])
        )
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA)
        self.assertContains(comprobante, "Comprobante de firma")
        self.assertContains(comprobante, evaluacion.firma_hash)
        _logout(self.client)

        self.assertTrue(
            Notificacion.objects.filter(tipo=CICLO_ACTIVADO, usuario=self.empleado).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(
                tipo=AUTOEVALUACION_ENVIADA, usuario=self.supervisor
            ).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(
                tipo=EVALUACION_SUPERVISOR_CERRADA, usuario=self.empleado
            ).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(
                tipo=CONFORMIDAD_FIRMADA, usuario=self.supervisor
            ).exists()
        )
        self.assertGreater(len(mail.outbox), 0)

        self.assertTrue(
            AuditLog.objects.filter(
                accion="activar", modelo="evaluaciones.cicloevaluacion"
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                accion="firmar_conformidad",
                modelo="evaluaciones.evaluacion",
            ).exists()
        )

        self.client.force_login(self.admin)
        pdf = self.client.get(
            reverse("reportes:iso_pdf"), {"ciclo": str(self.ciclo.pk)}
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], CONTENT_TYPE_PDF)
        excel = self.client.get(
            reverse("reportes:iso_excel"), {"ciclo": str(self.ciclo.pk)}
        )
        self.assertEqual(excel.status_code, 200)
        self.assertEqual(excel["Content-Type"], CONTENT_TYPE_EXCEL)
        self.assertTrue(
            AuditLog.objects.filter(accion=Accion.EXPORTAR).exists()
        )


class AdminRrhhAceptacionTests(CicloBaseTestCase):
    """UAT §13 punto 4: organigrama, puesto sin ciclo, plantilla, ciclo."""

    def test_organigrama_puesto_plantilla_ciclo_y_alta_usuario(self):
        self.client.force_login(self.admin)
        organigrama = self.client.get(reverse("organizacion:organigrama"))
        self.assertEqual(organigrama.status_code, 200)
        self.assertContains(organigrama, "Jefe")

        crear_puesto = self.client.post(
            reverse("organizacion:puesto_crear"),
            {
                "nombre": "Pasante UAT",
                "descripcion": "Alta sin ciclo circular",
                "area": str(self.area.pk),
                "puesto_superior": str(self.puesto_jefe.pk),
                "activo": "on",
                **_formset_puesto(),
            },
        )
        self.assertEqual(crear_puesto.status_code, 302)
        pasante = Puesto.objects.get(empresa=self.empresa, nombre="Pasante UAT")
        self.assertEqual(pasante.puesto_superior_id, self.puesto_jefe.pk)

        circular = self.client.post(
            reverse("organizacion:puesto_editar", args=[self.puesto_jefe.pk]),
            {
                "nombre": "Jefe",
                "descripcion": "",
                "area": "",
                "puesto_superior": str(self.puesto.pk),
                "activo": "on",
                **_formset_puesto(),
            },
        )
        self.assertEqual(circular.status_code, 200)
        self.assertContains(circular, "circular")
        self.puesto_jefe.refresh_from_db()
        self.assertIsNone(self.puesto_jefe.puesto_superior_id)

        competencia = make_competencia(self.empresa, nombre="UAT competencia")
        plantilla_post = self.client.post(
            reverse("evaluaciones:plantilla_crear"),
            {
                "nombre": "Plantilla UAT",
                "tipo": PlantillaEvaluacion.Tipo.MIXTA,
                "descripcion": "",
                "activa": "on",
                "puestos": [str(self.puesto.pk)],
                "criterios-TOTAL_FORMS": "1",
                "criterios-INITIAL_FORMS": "0",
                "criterios-MIN_NUM_FORMS": "0",
                "criterios-MAX_NUM_FORMS": "1000",
                "criterios-0-competencia": str(competencia.pk),
                "criterios-0-orden": "1",
                "criterios-0-escala_min": "1",
                "criterios-0-escala_max": "5",
                "criterios-0-ponderacion": "100",
            },
        )
        self.assertEqual(plantilla_post.status_code, 302)
        self.assertTrue(
            PlantillaEvaluacion.objects.filter(
                empresa=self.empresa, nombre="Plantilla UAT"
            ).exists()
        )

        ciclo_post = self.client.post(
            reverse("evaluaciones:ciclo_crear"),
            {
                "nombre": "Ciclo UAT extra",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=20)).isoformat(),
                "plantilla_default": str(self.plantilla.pk),
                "criterios_generales": "UAT",
            },
        )
        self.assertEqual(ciclo_post.status_code, 302)
        extra = CicloEvaluacion.objects.get(empresa=self.empresa, nombre="Ciclo UAT extra")
        self.assertEqual(extra.estado, CicloEvaluacion.Estado.BORRADOR)

        alta = self.client.post(
            reverse("cuentas:usuario_crear"),
            {
                "first_name": "Nuevo",
                "last_name": "UAT",
                "email": "nuevo.uat@empresa.test",
                "rol": "empleado",
            },
        )
        self.assertEqual(alta.status_code, 302)
        creado = Usuario.objects.get(empresa=self.empresa, email="nuevo.uat@empresa.test")
        self.assertTrue(
            AuditLog.objects.filter(
                accion=Accion.CREAR,
                modelo="cuentas.usuario",
                object_id=str(creado.pk),
            ).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(tipo=USUARIO_CREADO, usuario=creado).exists()
        )


class TenantYSuspensionAceptacionTests(TestCase):
    """UAT §13 puntos 6 y 7."""

    def setUp(self):
        self.datos = seed_demo()

    def test_admin_empresa_b_no_ve_datos_de_a(self):
        admin_b = self.datos["admin_b"]
        self.client.force_login(admin_b)
        usuarios = self.client.get(reverse("cuentas:usuarios"))
        self.assertEqual(usuarios.status_code, 200)
        self.assertNotContains(usuarios, EMAIL_EMPLEADO_1)
        self.assertNotContains(usuarios, EMAIL_SUPERVISOR)
        self.assertContains(usuarios, EMAIL_RRHH_B)

        ciclos = self.client.get(reverse("evaluaciones:ciclos"))
        self.assertEqual(ciclos.status_code, 200)
        self.assertNotContains(ciclos, "Ciclo demo 2026")

        ev_a = self.datos["evaluacion_pendiente"]
        self.assertIsNotNone(ev_a)
        ajena = self.client.get(reverse("evaluaciones:auto", args=[ev_a.pk]))
        self.assertEqual(ajena.status_code, 404)

        iso = self.client.get(reverse("reportes:iso"))
        self.assertEqual(iso.status_code, 200)
        self.assertNotContains(iso, "Ana Pérez")

    def test_suspender_empresa_a_bloquea_login(self):
        superadmin = self.datos["superadmin"]
        empresa_a = self.datos["empresa_a"]
        self.client.force_login(superadmin)
        suspender = self.client.post(
            reverse("empresas:suspender", args=[empresa_a.pk])
        )
        self.assertEqual(suspender.status_code, 302)
        empresa_a.refresh_from_db()
        self.assertEqual(empresa_a.estado, Empresa.Estado.SUSPENDIDA)
        _logout(self.client)

        login_emp = _login(self.client, EMAIL_EMPLEADO_1, DEMO_PASSWORD)
        self.assertEqual(login_emp.status_code, 200)
        self.assertContains(login_emp, "La empresa está suspendida.")
        self.assertFalse(login_emp.wsgi_request.user.is_authenticated)


class ResponsiveAceptacionTests(CicloBaseTestCase):
    """UAT §13 punto 10: templates clave y shell overflow/responsive."""

    def test_templates_clave_y_clases_overflow(self):
        login = self.client.get(reverse("cuentas:login"))
        self.assertEqual(login.status_code, 200)
        self.assertContains(login, 'name="viewport"', html=False)
        self.assertContains(login, "Iniciar sesión")

        self.client.force_login(self.admin)
        self.client.post(reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk]))
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)

        self.client.force_login(self.empleado)
        dash = self.client.get(reverse("app:dashboard"))
        self.assertEqual(dash.status_code, 200)
        self.assertContains(dash, "overflow-x-hidden")
        mias = self.client.get(reverse("evaluaciones:mias"))
        self.assertContains(mias, "overflow-x-auto")
        auto = self.client.get(reverse("evaluaciones:auto", args=[evaluacion.pk]))
        self.assertEqual(auto.status_code, 200)

        self.client.force_login(self.supervisor)
        equipo = self.client.get(reverse("evaluaciones:equipo"))
        self.assertEqual(equipo.status_code, 200)
        self.assertContains(equipo, "overflow-x-auto")


class SeedDemoAceptacionTests(TestCase):
    def test_seed_cubre_flujo_y_es_idempotente(self):
        primero = seed_demo()
        segundo = seed_demo()
        self.assertEqual(primero["empresa_a"].pk, segundo["empresa_a"].pk)
        self.assertEqual(
            Empresa.objects.filter(cuit__in=[EMPRESA_A_CUIT, EMPRESA_B_CUIT]).count(),
            2,
        )
        self.assertEqual(Usuario.objects.filter(email=EMAIL_EMPLEADO_1).count(), 1)
        self.assertEqual(Usuario.objects.filter(email=SUPERADMIN_EMAIL).count(), 1)

        ev1 = Evaluacion.objects.get(
            ciclo=segundo["ciclo"], evaluado=segundo["empleado_1"]
        )
        ev2 = Evaluacion.objects.get(
            ciclo=segundo["ciclo"], evaluado=segundo["empleado_2"]
        )
        ev3 = Evaluacion.objects.get(
            ciclo=segundo["ciclo"], evaluado=segundo["empleado_3"]
        )
        self.assertEqual(ev1.estado, Evaluacion.Estado.PENDIENTE_AUTO)
        self.assertEqual(ev2.estado, Evaluacion.Estado.AUTO_COMPLETA)
        self.assertEqual(ev3.estado, Evaluacion.Estado.CERRADA)
        self.assertEqual(segundo["ciclo"].estado, CicloEvaluacion.Estado.ACTIVO)

        for usuario in (
            segundo["empleado_1"],
            segundo["supervisor"],
            segundo["admin_a"],
            segundo["admin_b"],
            segundo["superadmin"],
        ):
            usuario.refresh_from_db()
            self.assertFalse(usuario.must_change_password)

        login = _login(self.client, EMAIL_EMPLEADO_1, DEMO_PASSWORD)
        self.assertEqual(login.status_code, 302)
        dash = self.client.get(reverse("app:dashboard"))
        self.assertEqual(dash.status_code, 200)

    def test_comando_seed_demo(self):
        call_command("seed_demo")
        self.assertTrue(Usuario.objects.filter(email=EMAIL_RRHH_A).exists())
        self.assertTrue(Usuario.objects.filter(email=EMAIL_SUPERVISOR).exists())
        self.assertTrue(Usuario.objects.filter(email=EMAIL_RRHH_B).exists())


class EnviarRecordatoriosAceptacionTests(CicloBaseTestCase):
    def test_comando_notifica_evaluaciones_pendientes(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk]))
        Notificacion.objects.filter(tipo=RECORDATORIO_VENCIMIENTO).delete()
        mail.outbox.clear()
        call_command("enviar_recordatorios")
        self.assertTrue(
            Notificacion.objects.filter(
                tipo=RECORDATORIO_VENCIMIENTO, usuario=self.empleado
            ).exists()
        )
        self.assertGreater(len(mail.outbox), 0)

    def test_dry_run_no_crea_notificaciones(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk]))
        Notificacion.objects.filter(tipo=RECORDATORIO_VENCIMIENTO).delete()
        call_command("enviar_recordatorios", dry_run=True)
        self.assertFalse(
            Notificacion.objects.filter(tipo=RECORDATORIO_VENCIMIENTO).exists()
        )
