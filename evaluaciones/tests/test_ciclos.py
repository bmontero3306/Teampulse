from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

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


def _formset_auto(evaluacion, puntaje=4, comentario="Ok", accion="enviar"):
    items = list(evaluacion.respuestas.order_by("criterio__orden", "pk"))
    data = {
        "items-TOTAL_FORMS": str(len(items)),
        "items-INITIAL_FORMS": str(len(items)),
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "accion": accion,
    }
    for i, item in enumerate(items):
        data[f"items-{i}-id"] = str(item.pk)
        data[f"items-{i}-puntaje_empleado"] = "" if puntaje is None else str(puntaje)
        data[f"items-{i}-comentario_empleado"] = comentario
    return data


def _formset_sup(evaluacion, puntaje=5, comentario="Bien", feedback="Feedback", accion="cerrar"):
    items = list(evaluacion.respuestas.order_by("criterio__orden", "pk"))
    data = {
        "items-TOTAL_FORMS": str(len(items)),
        "items-INITIAL_FORMS": str(len(items)),
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "feedback_supervisor": feedback,
        "accion": accion,
    }
    for i, item in enumerate(items):
        data[f"items-{i}-id"] = str(item.pk)
        data[f"items-{i}-puntaje_supervisor"] = "" if puntaje is None else str(puntaje)
        data[f"items-{i}-comentario_supervisor"] = comentario
    return data


class CicloBaseTestCase(TestCase):
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
        self.client.force_login(self.admin)
        lista = self.client.get(reverse("evaluaciones:ciclos"))
        self.assertContains(lista, "Ciclo Q1")
        self.assertNotContains(lista, "Ciclo secreto B")
        detalle = self.client.get(
            reverse("evaluaciones:ciclo_detalle", args=[ciclo_b.pk])
        )
        self.assertEqual(detalle.status_code, 404)

    def test_admin_crea_y_activa_por_vista(self):
        self.client.force_login(self.admin)
        crear = self.client.post(
            reverse("evaluaciones:ciclo_crear"),
            {
                "nombre": "Ciclo UI",
                "fecha_inicio": date.today().isoformat(),
                "fecha_cierre": (date.today() + timedelta(days=10)).isoformat(),
                "plantilla_default": str(self.plantilla.pk),
                "criterios_generales": "Criterios",
            },
        )
        self.assertEqual(crear.status_code, 302)
        ciclo = CicloEvaluacion.objects.get(nombre="Ciclo UI")
        self.assertEqual(ciclo.estado, CicloEvaluacion.Estado.BORRADOR)
        activar = self.client.post(
            reverse("evaluaciones:ciclo_activar", args=[ciclo.pk])
        )
        self.assertEqual(activar.status_code, 302)
        ciclo.refresh_from_db()
        self.assertEqual(ciclo.estado, CicloEvaluacion.Estado.ACTIVO)


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
