from datetime import date, timedelta
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import (
    make_area,
    make_ciclo,
    make_competencia,
    make_empresa,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaCriterio,
    PlantillaPuesto,
)
from evaluaciones.services import (
    activar_ciclo,
    cancelar_ciclo,
    guardar_autoevaluacion,
    pausar_ciclo,
    reasignar_evaluador,
)


def _criterio(plantilla, competencia, **kwargs):
    datos = {
        "plantilla": plantilla,
        "competencia": competencia,
        "orden": 1,
        "escala_min": 1,
        "escala_max": 5,
        "ponderacion": Decimal("100"),
        "comentario_empleado_obligatorio": False,
        "comentario_supervisor_obligatorio": False,
    }
    datos.update(kwargs)
    return PlantillaCriterio.objects.create(**datos)


class CicloBaseTestCase(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.area = make_area(self.empresa, nombre="Operaciones")
        self.puesto_jefe = make_puesto(self.empresa, nombre="Jefe")
        self.puesto = make_puesto(
            self.empresa,
            nombre="Analista",
            puesto_superior=self.puesto_jefe,
            area=self.area,
        )
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.supervisor = make_usuario(
            self.empresa,
            rol="supervisor",
            puesto=self.puesto_jefe,
            area=self.area,
            first_name="Jefa",
            last_name="Equipo",
        )
        self.empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            area=self.area,
            supervisor=self.supervisor,
            first_name="Ana",
            last_name="Pérez",
        )
        self.plantilla = make_plantilla(self.empresa, nombre="Plantilla anual")
        self.competencia = make_competencia(self.empresa, nombre="Comunicación")
        self.criterio = _criterio(self.plantilla, self.competencia)
        self.ciclo = make_ciclo(
            self.empresa,
            plantilla_default=self.plantilla,
            nombre="Ciclo Q1",
        )

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class ActivarCicloTests(CicloBaseTestCase):
    def test_no_activar_sin_empleados_con_puesto(self):
        empresa = make_empresa()
        plantilla = make_plantilla(empresa)
        _criterio(plantilla, make_competencia(empresa))
        ciclo = make_ciclo(empresa, plantilla_default=plantilla)
        admin = make_usuario(empresa, rol="admin_rrhh")
        with self.assertRaises(EvaluacionesError):
            activar_ciclo(ciclo, admin)

    def test_un_solo_ciclo_activo_por_empresa(self):
        activar_ciclo(self.ciclo, self.admin)
        otro = make_ciclo(
            self.empresa,
            plantilla_default=self.plantilla,
            nombre="Ciclo Q2",
        )
        with self.assertRaises(EvaluacionesError) as ctx:
            activar_ciclo(otro, self.admin)
        self.assertIn("ciclo activo", str(ctx.exception).lower())
        self.assertEqual(
            CicloEvaluacion.objects.filter(
                empresa=self.empresa, estado=CicloEvaluacion.Estado.ACTIVO
            ).count(),
            1,
        )

    def test_evaluador_por_usuario_supervisor(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.evaluador_id, self.supervisor.pk)
        self.assertFalse(evaluacion.sin_evaluador)
        self.assertEqual(
            evaluacion.respuestas.count(),
            1,
        )

    def test_evaluador_por_puesto_superior_si_no_hay_supervisor(self):
        self.empleado.supervisor = None
        self.empleado.save(update_fields=["supervisor"])
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.evaluador_id, self.supervisor.pk)
        self.assertFalse(evaluacion.sin_evaluador)

    def test_sin_evaluador_no_bloquea_el_ciclo(self):
        self.empleado.supervisor = None
        self.empleado.save(update_fields=["supervisor"])
        self.puesto.puesto_superior = None
        self.puesto.save(update_fields=["puesto_superior"])
        ciclo, sin_eval = activar_ciclo(self.ciclo, self.admin)
        self.assertEqual(ciclo.estado, CicloEvaluacion.Estado.ACTIVO)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertTrue(evaluacion.sin_evaluador)
        self.assertIsNone(evaluacion.evaluador)
        self.assertTrue(any(e.pk == evaluacion.pk for e in sin_eval))

    def test_usa_plantilla_del_puesto_si_existe(self):
        otra = make_plantilla(self.empresa, nombre="Plantilla de puesto")
        _criterio(otra, make_competencia(self.empresa, nombre="Otra competencia"))
        PlantillaPuesto.objects.create(plantilla=otra, puesto=self.puesto)
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.plantilla_id, otra.pk)

    def test_areas_vacias_incluye_toda_la_empresa(self):
        activar_ciclo(self.ciclo, self.admin)
        self.assertTrue(
            Evaluacion.objects.filter(ciclo=self.ciclo, evaluado=self.empleado).exists()
        )

    def test_tenant_empresa_a_no_ve_ciclos_de_b(self):
        empresa_b = make_empresa()
        plantilla_b = make_plantilla(empresa_b)
        ciclo_b = make_ciclo(
            empresa_b, plantilla_default=plantilla_b, nombre="Ciclo secreto B"
        )
        self._auth(self.admin)
        lista = self.client.get("/api/v1/ciclos/")
        self.assertEqual(lista.status_code, 200)
        nombres = [item["nombre"] for item in lista.data["results"]]
        self.assertIn("Ciclo Q1", nombres)
        self.assertNotIn("Ciclo secreto B", nombres)
        detalle = self.client.get(f"/api/v1/ciclos/{ciclo_b.pk}/")
        self.assertEqual(detalle.status_code, 404)

    def test_admin_crea_y_activa_por_api(self):
        self._auth(self.admin)
        crear = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Ciclo UI",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=10)).isoformat(),
                "plantilla_default": self.plantilla.pk,
                "criterios_generales": "Criterios",
            },
            format="json",
        )
        self.assertEqual(crear.status_code, 201, crear.content)
        ciclo = CicloEvaluacion.objects.get(nombre="Ciclo UI")
        self.assertEqual(ciclo.estado, CicloEvaluacion.Estado.BORRADOR)
        activar = self.client.post(f"/api/v1/ciclos/{ciclo.pk}/activar/")
        self.assertEqual(activar.status_code, 200, activar.content)
        ciclo.refresh_from_db()
        self.assertEqual(ciclo.estado, CicloEvaluacion.Estado.ACTIVO)

    def test_api_rechaza_cierre_anterior_al_inicio(self):
        self._auth(self.admin)
        response = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Ciclo inválido",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() - timedelta(days=1)).isoformat(),
                "plantilla_default": self.plantilla.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("anterior al inicio", response.content.decode())
        self.assertFalse(CicloEvaluacion.objects.filter(nombre="Ciclo inválido").exists())

    def test_api_rechaza_plantilla_inactiva_o_de_otra_empresa(self):
        self._auth(self.admin)
        inactiva = make_plantilla(self.empresa, nombre="Inactiva", activa=False)
        response = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Con inactiva",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=5)).isoformat(),
                "plantilla_default": inactiva.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        otra = make_empresa()
        ajena = make_plantilla(otra, nombre="Ajena")
        response = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Con ajena",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=5)).isoformat(),
                "plantilla_default": ajena.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(CicloEvaluacion.objects.filter(nombre="Con ajena").exists())

    def test_reprogramar_rechaza_fechas_invertidas(self):
        self._auth(self.admin)
        response = self.client.post(
            f"/api/v1/ciclos/{self.ciclo.pk}/reprogramar/",
            {
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() - timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("anterior al inicio", response.content.decode())


class CancelarYPausarTests(CicloBaseTestCase):
    def test_cancelar_ciclo_bloquea_nuevas_ediciones(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        cancelar_ciclo(self.ciclo, self.admin)
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.estado, CicloEvaluacion.Estado.CANCELADO)
        with self.assertRaises(EvaluacionesError) as ctx:
            guardar_autoevaluacion(
                evaluacion,
                {
                    evaluacion.respuestas.get().pk: {
                        "puntaje_empleado": 3,
                        "comentario_empleado": "x",
                    }
                },
                False,
                self.empleado,
            )
        self.assertIn("cancelado", str(ctx.exception).lower())
        self.assertTrue(Evaluacion.objects.filter(pk=evaluacion.pk).exists())

    def test_pausar_no_borra_historial(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        pausar_ciclo(self.ciclo, self.admin)
        self.assertTrue(Evaluacion.objects.filter(pk=evaluacion.pk).exists())
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.estado, CicloEvaluacion.Estado.PAUSADO)


class ReasignarEvaluadorTests(CicloBaseTestCase):
    def test_reasignar_falla_si_ya_tiene_evaluador(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertFalse(evaluacion.sin_evaluador)
        with self.assertRaises(EvaluacionesError):
            reasignar_evaluador(evaluacion, self.admin, self.admin)

    def test_reasignar_servicio_si_falta(self):
        self.empleado.supervisor = None
        self.empleado.save(update_fields=["supervisor"])
        self.puesto.puesto_superior = None
        self.puesto.save(update_fields=["puesto_superior"])
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertTrue(evaluacion.sin_evaluador)
        reasignar_evaluador(evaluacion, self.supervisor, self.admin)
        evaluacion.refresh_from_db()
        self.assertFalse(evaluacion.sin_evaluador)
        self.assertEqual(evaluacion.evaluador_id, self.supervisor.pk)

    def test_reasignar_por_api(self):
        self.empleado.supervisor = None
        self.empleado.save(update_fields=["supervisor"])
        self.puesto.puesto_superior = None
        self.puesto.save(update_fields=["puesto_superior"])
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertTrue(evaluacion.sin_evaluador)
        self._auth(self.admin)
        candidatos = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/reasignar/")
        self.assertEqual(candidatos.status_code, 200, candidatos.content)
        ids = [item["id"] for item in candidatos.data]
        self.assertIn(self.supervisor.pk, ids)
        self.assertNotIn(self.empleado.pk, ids)
        response = self.client.post(
            f"/api/v1/evaluaciones/{evaluacion.pk}/reasignar/",
            {"evaluador": self.supervisor.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        evaluacion.refresh_from_db()
        self.assertFalse(evaluacion.sin_evaluador)
        self.assertEqual(evaluacion.evaluador_id, self.supervisor.pk)
