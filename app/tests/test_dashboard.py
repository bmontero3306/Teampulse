from django.test import TestCase
from django.urls import reverse

from app.tests.factories import (
    make_ciclo,
    make_empresa,
    make_evaluacion,
    make_puesto,
    make_usuario,
)
from evaluaciones.models import CicloEvaluacion, Evaluacion


class DashboardViewTests(TestCase):
    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_empleado_ve_pendientes_y_empty_state(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel · TeamPulse")
        self.assertContains(response, 'data-widget="pendientes"')
        self.assertContains(response, "No hay ciclo activo")
        self.assertContains(response, 'data-acceso="mias"')
        self.assertNotContains(response, 'data-widget="kpis"')
        self.assertNotContains(response, 'data-widget="equipo"')
        self.assertNotContains(response, 'data-widget="empresas"')
        self.assertIsNone(response.context["kpis"])

    def test_supervisor_ve_equipo_y_pendientes(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="supervisor")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-widget="equipo"')
        self.assertContains(response, 'data-widget="pendientes"')
        self.assertContains(response, "No hay colaboradores para evaluar")
        self.assertNotContains(response, 'data-widget="kpis"')

    def test_admin_rrhh_ve_kpis_en_cero(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="admin_rrhh")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-widget="kpis"')
        self.assertContains(response, "Participantes")
        self.assertContains(response, "Autoevaluaciones")
        self.assertContains(response, "Sin evaluador")
        self.assertContains(
            response,
            "Los indicadores se van a completar cuando haya un ciclo activo.",
        )
        self.assertEqual(response.context["kpis"]["participantes"], 0)
        self.assertEqual(response.context["kpis"]["auto"], 0)
        self.assertEqual(response.context["kpis"]["supervisor"], 0)
        self.assertEqual(response.context["kpis"]["firmadas"], 0)
        self.assertEqual(response.context["kpis"]["sin_evaluador"], 0)
        self.assertNotContains(response, 'data-widget="pendientes"')

    def test_superadmin_lista_empresas(self):
        empresa = make_empresa(nombre="Acme Industrial", estado="activa")
        usuario = make_usuario(None, rol="superadmin")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-widget="empresas"')
        self.assertContains(response, "Acme Industrial")
        self.assertContains(response, "Activa")
        self.assertContains(response, 'href="/empresas/"')
        self.assertContains(response, "overflow-x-auto")

    def test_superadmin_sin_empresas_muestra_empty_state(self):
        usuario = make_usuario(None, rol="superadmin")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todavía no hay empresas registradas")

    def test_topbar_muestra_nombre_rol_y_logout_post(self):
        empresa = make_empresa()
        usuario = make_usuario(
            empresa,
            rol="empleado",
            first_name="Ana",
            last_name="Pérez",
        )
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Empleado")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, reverse("cuentas:logout"))
        self.assertContains(response, empresa.nombre)
        self.assertContains(response, "overflow-x-hidden")


class DashboardKpisRealesTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.puesto = make_puesto(self.empresa)
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.ciclo = make_ciclo(
            self.empresa,
            estado=CicloEvaluacion.Estado.ACTIVO,
            nombre="Ciclo Q1",
        )

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

        self.client.force_login(self.admin)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ciclo Q1")
        self.assertNotContains(
            response,
            "Los indicadores se van a completar cuando haya un ciclo activo.",
        )
        kpis = response.context["kpis"]
        self.assertEqual(kpis["participantes"], 5)
        self.assertEqual(kpis["auto"], 4)
        self.assertEqual(kpis["supervisor"], 3)
        self.assertEqual(kpis["firmadas"], 2)
        self.assertEqual(kpis["sin_evaluador"], 1)
        self.assertContains(response, 'data-kpi="participantes"')
        self.assertContains(response, 'data-widget="kpis"')

    def test_kpis_no_mezclan_otra_empresa(self):
        self._eval(Evaluacion.Estado.CERRADA)
        empresa_b = make_empresa()
        puesto_b = make_puesto(empresa_b)
        ciclo_b = make_ciclo(empresa_b, estado=CicloEvaluacion.Estado.ACTIVO)
        empleado_b = make_usuario(empresa_b, rol="empleado", puesto=puesto_b)
        make_evaluacion(ciclo_b, empleado_b, estado=Evaluacion.Estado.CERRADA)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("app:dashboard"))
        kpis = response.context["kpis"]
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
        make_evaluacion(
            self.ciclo,
            empleado,
            estado=Evaluacion.Estado.PENDIENTE_AUTO,
        )
        self._eval(Evaluacion.Estado.CERRADA)

        self.client.force_login(empleado)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ciclo Q1")
        self.assertContains(response, 'data-widget="pendientes"')
        self.assertContains(response, "Completar autoevaluación")
        self.assertContains(response, 'data-acceso="auto"')
        self.assertContains(response, 'data-acceso="mias"')
        self.assertNotContains(response, 'data-widget="kpis"')
        self.assertNotContains(response, "Sin evaluador")
        self.assertNotContains(response, "Participantes")
        self.assertIsNone(response.context["kpis"])

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
        self.client.force_login(empleado)
        response = self.client.get(reverse("app:dashboard"))
        self.assertContains(response, "Firmar conformidad")
        self.assertContains(response, 'data-acceso="firmar"')
        self.assertContains(
            response,
            reverse("evaluaciones:resultado", args=[evaluacion.pk]),
        )

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
        self.client.force_login(supervisor)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-widget="equipo"')
        self.assertContains(response, 'data-equipo="completitud"')
        self.assertContains(response, "50%")
        self.assertContains(response, 'data-alerta="sin-autoevaluacion"')
        self.assertContains(response, "Mario Pendiente")
        self.assertContains(response, reverse("evaluaciones:equipo"))
        self.assertEqual(response.context["equipo_resumen"]["total"], 2)
        self.assertEqual(response.context["equipo_resumen"]["completitud"], 50)
        self.assertEqual(len(response.context["equipo_resumen"]["alertas_sin_auto"]), 1)
        self.assertNotContains(response, 'data-widget="kpis"')
        self.assertContains(response, "overflow-x-auto")
