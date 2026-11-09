from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from rest_framework.test import APITestCase

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
from evaluaciones.pdf import CONTENT_TYPE_PDF
from evaluaciones.tests.test_ciclos import CicloBaseTestCase
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
from reportes.services import CONTENT_TYPE_EXCEL


def _login(client, email, password="clave-test-123"):
    response = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    token = response.data.get("token") if getattr(response, "data", None) else None
    if response.status_code == 200 and token:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    else:
        client.credentials()
    return response


def _logout(client):
    response = client.post("/api/v1/auth/logout/")
    client.credentials()
    return response


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


class RecorridoFlujoAceptacionTests(CicloBaseTestCase):
    """UAT §13 puntos 1–3, 5, 8 (activar/firma/export) y 9."""

    def test_login_auto_supervisor_firma_export_audit_notif(self):
        login_admin = _login(self.client, self.admin.email)
        self.assertEqual(login_admin.status_code, 200, login_admin.content)
        activar = self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/")
        self.assertEqual(activar.status_code, 200, activar.content)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTOEVALUACION)
        _logout(self.client)

        login_emp = _login(self.client, self.empleado.email)
        self.assertEqual(login_emp.status_code, 200, login_emp.content)
        mias = self.client.get("/api/v1/evaluaciones/mias/")
        self.assertEqual(mias.status_code, 200, mias.content)
        self.assertTrue(any(item["ciclo_nombre"] == "Ciclo Q1" for item in mias.data))
        self.assertTrue(
            any(item["estado"] == Evaluacion.Estado.AUTOEVALUACION for item in mias.data)
        )
        auto_get = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/")
        self.assertEqual(auto_get.status_code, 200, auto_get.content)

        item = evaluacion.respuestas.get()
        borrador = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": False,
                "respuestas": [
                    {"id": item.pk, "puntaje_empleado": 3, "comentario_empleado": ""}
                ],
            },
            format="json",
        )
        self.assertEqual(borrador.status_code, 200, borrador.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTOEVALUACION)
        self.assertTrue(borrador.data["en_borrador"])

        enviar = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": True,
                "respuestas": [
                    {
                        "id": item.pk,
                        "puntaje_empleado": 4,
                        "comentario_empleado": "Listo UAT",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(enviar.status_code, 200, enviar.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.SUPERVISOR)
        _logout(self.client)

        login_sup = _login(self.client, self.supervisor.email)
        self.assertEqual(login_sup.status_code, 200, login_sup.content)
        equipo = self.client.get("/api/v1/evaluaciones/equipo/")
        self.assertEqual(equipo.status_code, 200, equipo.content)
        self.assertTrue(
            any(item["evaluado"]["first_name"] == self.empleado.first_name for item in equipo.data)
        )
        ciego = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/")
        self.assertEqual(ciego.status_code, 200, ciego.content)
        self.assertNotIn("Listo UAT", ciego.content.decode())
        self.assertIsNone(ciego.data["respuestas"][0]["puntaje_empleado"])
        self.assertEqual(ciego.data["respuestas"][0]["comentario_empleado"], "")
        cerrar = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/",
            {
                "cerrar": True,
                "habilitar_reunion": False,
                "feedback_supervisor": "Feedback UAT",
                "respuestas": [
                    {
                        "id": item.pk,
                        "puntaje_supervisor": 5,
                        "comentario_supervisor": "Ok UAT",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(cerrar.status_code, 200, cerrar.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)

        comparacion = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertEqual(comparacion.status_code, 200, comparacion.content)
        fila = comparacion.data["respuestas"][0]
        self.assertEqual(fila["comentario_empleado"], "Listo UAT")
        self.assertEqual(fila["comentario_supervisor"], "Ok UAT")
        self.assertEqual(fila["brecha"], 1)
        self.assertEqual(comparacion.data["feedback_supervisor"], "Feedback UAT")
        self.assertFalse((comparacion.data["reunion_notas"] or "").strip())
        self.assertFalse(comparacion.data["puede_firmar"])
        _logout(self.client)

        _login(self.client, self.empleado.email)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertEqual(resultado.status_code, 200, resultado.content)
        self.assertEqual(resultado.data["feedback_supervisor"], "Feedback UAT")
        self.assertTrue(resultado.data["puede_firmar"])
        firmar = self.client.post(
            f"/api/v1/evaluaciones/{evaluacion.pk}/firmar/",
            {"observacion": ""},
            format="json",
        )
        self.assertEqual(firmar.status_code, 200, firmar.content)
        comprobante = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA)
        self.assertEqual(comprobante.data["firma_hash"], evaluacion.firma_hash)
        self.assertTrue(evaluacion.firma_hash)
        pdf = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], CONTENT_TYPE_PDF)
        self.assertTrue(pdf.content.startswith(b"%PDF"), "La respuesta no es un PDF")
        self.assertTrue(
            evaluacion.firma_hash.encode("ascii") in pdf.content,
            "Falta el hash de firma digital",
        )
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

        _login(self.client, self.admin.email)
        pdf = self.client.get(
            "/api/v1/reportes/iso/pdf/", {"ciclo": str(self.ciclo.pk)}
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], CONTENT_TYPE_PDF)
        excel = self.client.get(
            "/api/v1/reportes/iso/excel/", {"ciclo": str(self.ciclo.pk)}
        )
        self.assertEqual(excel.status_code, 200)
        self.assertEqual(excel["Content-Type"], CONTENT_TYPE_EXCEL)
        self.assertTrue(AuditLog.objects.filter(accion=Accion.EXPORTAR).exists())


class AdminRrhhAceptacionTests(CicloBaseTestCase):
    """UAT §13 punto 4: organigrama, puesto sin ciclo, plantilla, ciclo, alta de usuario."""

    def test_organigrama_puesto_plantilla_ciclo_y_alta_usuario(self):
        _login(self.client, self.admin.email)
        organigrama = self.client.get("/api/v1/organigrama/")
        self.assertEqual(organigrama.status_code, 200, organigrama.content)
        self.assertIn("Jefe", [nodo["nombre"] for nodo in organigrama.data["raices"]])

        crear_puesto = self.client.post(
            "/api/v1/puestos/",
            {
                "nombre": "Pasante UAT",
                "descripcion": "Alta sin ciclo circular",
                "area": self.area.pk,
                "puesto_superior": self.puesto_jefe.pk,
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(crear_puesto.status_code, 201, crear_puesto.content)
        pasante = Puesto.objects.get(empresa=self.empresa, nombre="Pasante UAT")
        self.assertEqual(pasante.puesto_superior_id, self.puesto_jefe.pk)

        circular = self.client.patch(
            f"/api/v1/puestos/{self.puesto_jefe.pk}/",
            {"puesto_superior": self.puesto.pk},
            format="json",
        )
        self.assertEqual(circular.status_code, 400, circular.content)
        self.assertIn("circular", str(circular.data["puesto_superior"]).lower())
        self.puesto_jefe.refresh_from_db()
        self.assertIsNone(self.puesto_jefe.puesto_superior_id)

        competencia = make_competencia(self.empresa, nombre="UAT competencia")
        plantilla_post = self.client.post(
            "/api/v1/plantillas/",
            {
                "nombre": "Plantilla UAT",
                "tipo": PlantillaEvaluacion.Tipo.MIXTA,
                "descripcion": "",
                "activa": True,
                "puestos": [self.puesto.pk],
                "criterios": [
                    {
                        "competencia": competencia.pk,
                        "categoria": "",
                        "tipo_item": "escala",
                        "orden": 1,
                        "escala_min": 1,
                        "escala_max": 5,
                        "ponderacion": "100",
                        "comentario_empleado_obligatorio": False,
                        "comentario_supervisor_obligatorio": False,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(plantilla_post.status_code, 201, plantilla_post.content)
        self.assertTrue(
            PlantillaEvaluacion.objects.filter(
                empresa=self.empresa, nombre="Plantilla UAT"
            ).exists()
        )

        ciclo_post = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Ciclo UAT extra",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=20)).isoformat(),
                "plantilla_default": self.plantilla.pk,
                "criterios_generales": "UAT",
            },
            format="json",
        )
        self.assertEqual(ciclo_post.status_code, 201, ciclo_post.content)
        extra = CicloEvaluacion.objects.get(empresa=self.empresa, nombre="Ciclo UAT extra")
        self.assertEqual(extra.estado, CicloEvaluacion.Estado.BORRADOR)

        alta = self.client.post(
            "/api/v1/usuarios/",
            {
                "first_name": "Nuevo",
                "last_name": "UAT",
                "email": "nuevo.uat@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(alta.status_code, 201, alta.content)
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


class TenantYSuspensionAceptacionTests(APITestCase):
    """UAT §13 puntos 6 y 7."""

    def setUp(self):
        self.datos = seed_demo()

    def test_admin_empresa_b_no_ve_datos_de_a(self):
        admin_b = self.datos["admin_b"]
        _login(self.client, admin_b.email, DEMO_PASSWORD)
        usuarios = self.client.get("/api/v1/usuarios/")
        self.assertEqual(usuarios.status_code, 200, usuarios.content)
        emails = [item["email"] for item in _results(usuarios)]
        self.assertNotIn(EMAIL_EMPLEADO_1, emails)
        self.assertNotIn(EMAIL_SUPERVISOR, emails)
        self.assertIn(EMAIL_RRHH_B, emails)

        ciclos = self.client.get("/api/v1/ciclos/")
        self.assertEqual(ciclos.status_code, 200, ciclos.content)
        nombres = [item["nombre"] for item in _results(ciclos)]
        self.assertNotIn("Ciclo demo 2026", nombres)

        ev_a = self.datos["evaluacion_pendiente"]
        self.assertIsNotNone(ev_a)
        ajena = self.client.get(f"/api/v1/evaluaciones/{ev_a.pk}/autoevaluacion/")
        self.assertEqual(ajena.status_code, 404)

        iso = self.client.get("/api/v1/reportes/iso/")
        self.assertEqual(iso.status_code, 200, iso.content)
        evaluados = [fila["evaluado"] for fila in iso.data["evaluaciones"]]
        self.assertNotIn("Ana Pérez", evaluados)

    def test_suspender_empresa_a_bloquea_login(self):
        superadmin = self.datos["superadmin"]
        empresa_a = self.datos["empresa_a"]
        _login(self.client, superadmin.email, DEMO_PASSWORD)
        suspender = self.client.post(f"/api/v1/empresas/{empresa_a.pk}/suspender/")
        self.assertEqual(suspender.status_code, 200, suspender.content)
        empresa_a.refresh_from_db()
        self.assertEqual(empresa_a.estado, Empresa.Estado.SUSPENDIDA)
        _logout(self.client)

        login_emp = _login(self.client, EMAIL_EMPLEADO_1, DEMO_PASSWORD)
        self.assertEqual(login_emp.status_code, 400, login_emp.content)
        self.assertIn("suspendida", login_emp.data["detail"])
        self.assertNotIn("token", login_emp.data)


class DashboardAceptacionTests(CicloBaseTestCase):
    """UAT §13 punto 10: las pantallas de login, panel, mías y equipo salen por la API."""

    def test_login_dashboard_mias_y_equipo(self):
        anonimo = self.client.get("/api/v1/dashboard/")
        self.assertEqual(anonimo.status_code, 401)

        _login(self.client, self.admin.email)
        activar = self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/")
        self.assertEqual(activar.status_code, 200, activar.content)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        _logout(self.client)

        _login(self.client, self.empleado.email)
        dash = self.client.get("/api/v1/dashboard/")
        self.assertEqual(dash.status_code, 200, dash.content)
        self.assertEqual(dash.data["ciclo_activo"]["nombre"], "Ciclo Q1")
        self.assertTrue(dash.data["mostrar_pendientes"])
        self.assertTrue(any("Completar" in item["accion"] for item in dash.data["pendientes"]))
        mias = self.client.get("/api/v1/evaluaciones/mias/")
        self.assertEqual(mias.status_code, 200, mias.content)
        self.assertTrue(any(item["ciclo_nombre"] == "Ciclo Q1" for item in mias.data))
        auto = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/")
        self.assertEqual(auto.status_code, 200, auto.content)
        _logout(self.client)

        _login(self.client, self.supervisor.email)
        equipo = self.client.get("/api/v1/evaluaciones/equipo/")
        self.assertEqual(equipo.status_code, 200, equipo.content)
        self.assertTrue(
            any(item["evaluado"]["first_name"] == self.empleado.first_name for item in equipo.data)
        )
        panel = self.client.get("/api/v1/dashboard/")
        self.assertEqual(panel.status_code, 200, panel.content)
        self.assertTrue(panel.data["mostrar_equipo"])
        self.assertEqual(panel.data["equipo"]["href"], "/evaluaciones/equipo")


class SeedDemoAceptacionTests(APITestCase):
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
        self.assertEqual(ev1.estado, Evaluacion.Estado.AUTOEVALUACION)
        self.assertEqual(ev2.estado, Evaluacion.Estado.SUPERVISOR)
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
        self.assertEqual(login.status_code, 200, login.content)
        dash = self.client.get("/api/v1/dashboard/")
        self.assertEqual(dash.status_code, 200, dash.content)
        self.assertEqual(dash.data["ciclo_activo"]["nombre"], "Ciclo demo 2026")

    def test_comando_seed_demo(self):
        call_command("seed_demo")
        self.assertTrue(Usuario.objects.filter(email=EMAIL_RRHH_A).exists())
        self.assertTrue(Usuario.objects.filter(email=EMAIL_SUPERVISOR).exists())
        self.assertTrue(Usuario.objects.filter(email=EMAIL_RRHH_B).exists())


class EnviarRecordatoriosAceptacionTests(CicloBaseTestCase):
    def test_comando_notifica_evaluaciones_pendientes(self):
        _login(self.client, self.admin.email)
        activar = self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/")
        self.assertEqual(activar.status_code, 200, activar.content)
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
        _login(self.client, self.admin.email)
        activar = self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/")
        self.assertEqual(activar.status_code, 200, activar.content)
        Notificacion.objects.filter(tipo=RECORDATORIO_VENCIMIENTO).delete()
        call_command("enviar_recordatorios", dry_run=True)
        self.assertFalse(
            Notificacion.objects.filter(tipo=RECORDATORIO_VENCIMIENTO).exists()
        )


class SpaCatchAllTests(APITestCase):
    def test_anonimo_en_raiz_y_dashboard_cae_en_la_spa(self):
        index = Path(settings.SPA_ROOT) / "index.html"
        esperado = index.read_bytes() if index.is_file() else None
        for ruta in ("/", "/dashboard"):
            response = self.client.get(ruta)
            if esperado is None:
                self.assertEqual(response.status_code, 503, ruta)
                self.assertIn("frontend", response.content.decode())
                continue
            self.assertEqual(response.status_code, 200, ruta)
            self.assertIn("text/html", response["Content-Type"])
            cuerpo = b"".join(response.streaming_content)
            self.assertEqual(cuerpo, esperado)
