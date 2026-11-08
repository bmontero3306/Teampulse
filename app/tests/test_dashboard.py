from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import (
    make_ciclo,
    make_empresa,
    make_evaluacion,
    make_puesto,
    make_usuario,
)
from evaluaciones.models import CicloEvaluacion, Evaluacion


def _claves(items, campo="clave"):
    return [item[campo] for item in items]


class DashboardViewTests(APITestCase):
    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_dashboard_requiere_token(self):
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 401)

    def test_empleado_ve_pendientes_sin_ciclo(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        self._auth(usuario)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertIsNone(data["ciclo_activo"])
        self.assertIsNone(data["kpis"])
        self.assertEqual(data["pendientes"], [])
        self.assertEqual(_claves(data["accesos_rapidos"]), ["mias"])
        self.assertEqual(data["accesos_rapidos"][0]["href"], "/evaluaciones/mias")
        self.assertTrue(data["mostrar_pendientes"])
        self.assertFalse(data["mostrar_kpis"])
        self.assertFalse(data["mostrar_equipo"])
        self.assertFalse(data["mostrar_empresas"])
        self.assertIsNone(data["equipo"])

    def test_supervisor_ve_equipo_y_pendientes(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="supervisor")
        self._auth(usuario)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertTrue(data["mostrar_equipo"])
        self.assertTrue(data["mostrar_pendientes"])
        self.assertFalse(data["mostrar_kpis"])
        self.assertIsNone(data["kpis"])
        self.assertIsNone(data["ciclo_activo"])
        self.assertEqual(data["equipo"]["total"], 0)
        self.assertEqual(data["equipo"]["completitud"], 0)
        self.assertEqual(data["equipo"]["evaluaciones"], [])
        self.assertEqual(data["equipo"]["href"], "/evaluaciones/equipo")

    def test_admin_rrhh_ve_kpis_en_cero(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="admin_rrhh")
        self._auth(usuario)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        kpis = response.data["kpis"]
        self.assertEqual(kpis["participantes"], 0)
        self.assertEqual(kpis["auto"], 0)
        self.assertEqual(kpis["supervisor"], 0)
        self.assertEqual(kpis["firmadas"], 0)
        self.assertEqual(kpis["sin_evaluador"], 0)
        self.assertIsNone(response.data["ciclo_activo"])
        self.assertTrue(response.data["mostrar_kpis"])
        self.assertFalse(response.data["mostrar_pendientes"])
        self.assertEqual(response.data["pendientes"], [])

    def test_superadmin_lista_empresas(self):
        empresa = make_empresa(nombre="Acme Industrial", estado="activa")
        usuario = make_usuario(None, rol="superadmin")
        self._auth(usuario)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["mostrar_empresas"])
        self.assertFalse(response.data["mostrar_kpis"])
        self.assertEqual(
            response.data["empresas_plataforma"],
            [{"id": empresa.pk, "nombre": "Acme Industrial", "estado": "activa"}],
        )

    def test_superadmin_sin_empresas(self):
        usuario = make_usuario(None, rol="superadmin")
        self._auth(usuario)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["empresas_plataforma"], [])
        self.assertTrue(response.data["mostrar_empresas"])


class DashboardKpisRealesTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.puesto = make_puesto(self.empresa)
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.ciclo = make_ciclo(
            self.empresa,
            estado=CicloEvaluacion.Estado.ACTIVO,
            nombre="Ciclo Q1",
        )

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _eval(self, estado, **kwargs):
        empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            **kwargs.pop("usuario_kwargs", {}),
        )
        return make_evaluacion(self.ciclo, empleado, estado=estado, **kwargs)

    def test_admin_ve_kpis_numericos_con_ciclo_activo(self):
        supervisor = make_usuario(self.empresa, rol="supervisor", puesto=self.puesto)
        self._eval(Evaluacion.Estado.PENDIENTE_AUTO, evaluador=None, sin_evaluador=True)
        self._eval(
            Evaluacion.Estado.AUTO_COMPLETA,
            evaluador=supervisor,
            sin_evaluador=False,
        )
        self._eval(
            Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
            evaluador=supervisor,
            sin_evaluador=False,
        )
        self._eval(
            Evaluacion.Estado.CERRADA,
            evaluador=supervisor,
            sin_evaluador=False,
        )
        self._eval(
            Evaluacion.Estado.CERRADA_CON_OBS,
            evaluador=supervisor,
            sin_evaluador=False,
        )

        self._auth(self.admin)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ciclo_activo"]["nombre"], "Ciclo Q1")
        self.assertEqual(response.data["ciclo_activo"]["id"], self.ciclo.pk)
        kpis = response.data["kpis"]
        self.assertEqual(kpis["participantes"], 5)
        self.assertEqual(kpis["auto"], 4)
        self.assertEqual(kpis["supervisor"], 3)
        self.assertEqual(kpis["firmadas"], 2)
        self.assertEqual(kpis["sin_evaluador"], 1)

    def test_kpis_no_mezclan_otra_empresa(self):
        self._eval(Evaluacion.Estado.CERRADA)
        empresa_b = make_empresa()
        puesto_b = make_puesto(empresa_b)
        ciclo_b = make_ciclo(empresa_b, estado=CicloEvaluacion.Estado.ACTIVO)
        empleado_b = make_usuario(empresa_b, rol="empleado", puesto=puesto_b)
        make_evaluacion(ciclo_b, empleado_b, estado=Evaluacion.Estado.CERRADA)

        self._auth(self.admin)
        response = self.client.get("/api/v1/dashboard/")
        kpis = response.data["kpis"]
        self.assertEqual(kpis["participantes"], 1)
        self.assertEqual(kpis["firmadas"], 1)

    def test_empleado_no_ve_kpis_de_rrhh_con_ciclo_activo(self):
        empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            first_name="Carla",
            last_name="López",
        )
        evaluacion = make_evaluacion(
            self.ciclo,
            empleado,
            estado=Evaluacion.Estado.PENDIENTE_AUTO,
        )
        self._eval(Evaluacion.Estado.CERRADA)

        self._auth(empleado)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ciclo_activo"]["nombre"], "Ciclo Q1")
        self.assertIsNone(response.data["kpis"])
        self.assertFalse(response.data["mostrar_kpis"])
        self.assertTrue(response.data["mostrar_pendientes"])
        self.assertEqual(len(response.data["pendientes"]), 1)
        pendiente = response.data["pendientes"][0]
        self.assertEqual(pendiente["accion"], "Completar autoevaluación")
        self.assertEqual(pendiente["estado"], Evaluacion.Estado.PENDIENTE_AUTO)
        self.assertEqual(pendiente["tipo"], "auto")
        self.assertEqual(
            pendiente["href"],
            f"/evaluaciones/{evaluacion.pk}/autoevaluacion",
        )
        self.assertEqual(pendiente["ciclo"], "Ciclo Q1")
        self.assertEqual(
            _claves(response.data["accesos_rapidos"]),
            ["mias", "auto"],
        )

    def test_empleado_ve_acceso_a_firmar(self):
        empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
        )
        evaluacion = make_evaluacion(
            self.ciclo,
            empleado,
            estado=Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
        )
        self._auth(empleado)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.data["pendientes"][0]["accion"], "Firmar conformidad")
        self.assertEqual(
            response.data["pendientes"][0]["href"],
            f"/evaluaciones/{evaluacion.pk}/resultado",
        )
        self.assertIn("firmar", _claves(response.data["accesos_rapidos"]))

    def test_supervisor_ve_completitud_y_alertas(self):
        supervisor = make_usuario(
            self.empresa,
            rol="supervisor",
            puesto=self.puesto,
            first_name="Sofía",
            last_name="Jefe",
        )
        pendiente = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            first_name="Mario",
            last_name="Pendiente",
            supervisor=supervisor,
        )
        completa = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            first_name="Elena",
            last_name="Lista",
            supervisor=supervisor,
        )
        make_evaluacion(
            self.ciclo,
            pendiente,
            evaluador=supervisor,
            estado=Evaluacion.Estado.PENDIENTE_AUTO,
        )
        make_evaluacion(
            self.ciclo,
            completa,
            evaluador=supervisor,
            estado=Evaluacion.Estado.AUTO_COMPLETA,
        )
        self._auth(supervisor)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        equipo = response.data["equipo"]
        self.assertEqual(equipo["total"], 2)
        self.assertEqual(equipo["completitud"], 50)
        self.assertEqual(equipo["href"], "/evaluaciones/equipo")
        self.assertEqual(len(equipo["alertas_sin_auto"]), 1)
        self.assertEqual(equipo["alertas_sin_auto"][0]["evaluado"], "Mario Pendiente")
        nombres = {item["evaluado"] for item in equipo["evaluaciones"]}
        self.assertEqual(nombres, {"Mario Pendiente", "Elena Lista"})
        por_nombre = {item["evaluado"]: item for item in equipo["evaluaciones"]}
        self.assertEqual(
            por_nombre["Mario Pendiente"]["estado_display"],
            "Pendiente de autoevaluación",
        )
        self.assertIsNone(response.data["kpis"])
        self.assertFalse(response.data["mostrar_kpis"])

    def test_pendiente_comparacion_cuenta_en_kpis_y_pendientes(self):
        empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
        )
        make_evaluacion(
            self.ciclo,
            empleado,
            estado=Evaluacion.Estado.PENDIENTE_COMPARACION,
        )
        self._auth(self.admin)
        kpis = self.client.get("/api/v1/dashboard/").data["kpis"]
        self.assertEqual(kpis["auto"], 1)
        self.assertEqual(kpis["supervisor"], 1)
        self.assertEqual(kpis["firmadas"], 0)

        self._auth(empleado)
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.data["pendientes"][0]["accion"], "Ver comparación")
        self.assertEqual(response.data["pendientes"][0]["tipo"], "comparacion")
        self.assertIn("comparacion", _claves(response.data["accesos_rapidos"]))
