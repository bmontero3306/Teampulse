from django.urls import reverse

from app.tests.factories import (
    make_competencia,
    make_ciclo,
    make_empresa,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.models import CicloEvaluacion, Evaluacion
from evaluaciones.services import (
    activar_ciclo,
    calcular_firma_hash,
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
)
from evaluaciones.tests.test_ciclos import (
    CicloBaseTestCase,
    _formset_auto,
    _formset_sup,
    _criterio,
)


class AislamientoEmpleadoTests(CicloBaseTestCase):
    def test_empleado_no_ve_evaluaciones_de_otro(self):
        otro = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            area=self.area,
            supervisor=self.supervisor,
            first_name="Luis",
            last_name="Otro",
        )
        activar_ciclo(self.ciclo, self.admin)
        eval_propia = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        eval_ajena = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=otro)

        self.client.force_login(self.empleado)
        mias = self.client.get(reverse("evaluaciones:mias"))
        self.assertEqual(mias.status_code, 200)
        self.assertContains(mias, "Ciclo Q1")
        self.assertNotContains(mias, otro.email)

        propia = self.client.get(reverse("evaluaciones:auto", args=[eval_propia.pk]))
        self.assertEqual(propia.status_code, 200)
        ajena = self.client.get(reverse("evaluaciones:auto", args=[eval_ajena.pk]))
        self.assertEqual(ajena.status_code, 403)
        resultado_ajeno = self.client.get(
            reverse("evaluaciones:resultado", args=[eval_ajena.pk])
        )
        self.assertEqual(resultado_ajeno.status_code, 403)

    def test_tenant_no_ve_evaluaciones_de_otra_empresa(self):
        empresa_b = make_empresa()
        puesto_b = make_puesto(empresa_b)
        empleado_b = make_usuario(empresa_b, rol="empleado", puesto=puesto_b)
        plantilla_b = make_plantilla(empresa_b)
        _criterio(plantilla_b, make_competencia(empresa_b))
        ciclo_b = make_ciclo(empresa_b, plantilla_default=plantilla_b)
        admin_b = make_usuario(empresa_b, rol="admin_rrhh")
        activar_ciclo(ciclo_b, admin_b)
        eval_b = Evaluacion.objects.get(ciclo=ciclo_b, evaluado=empleado_b)

        self.client.force_login(self.empleado)
        response = self.client.get(reverse("evaluaciones:auto", args=[eval_b.pk]))
        self.assertEqual(response.status_code, 404)


class SupervisorAntesDeAutoTests(CicloBaseTestCase):
    def test_supervisor_no_evalua_antes_de_auto(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_AUTO)

        with self.assertRaises(EvaluacionesError):
            guardar_eval_supervisor(
                evaluacion,
                {
                    evaluacion.respuestas.get().pk: {
                        "puntaje_supervisor": 4,
                        "comentario_supervisor": "ok",
                    }
                },
                "feedback",
                True,
                self.supervisor,
            )

        self.client.force_login(self.supervisor)
        get_resp = self.client.get(
            reverse("evaluaciones:supervisar", args=[evaluacion.pk])
        )
        self.assertEqual(get_resp.status_code, 403)
        post_resp = self.client.post(
            reverse("evaluaciones:supervisar", args=[evaluacion.pk]),
            _formset_sup(evaluacion),
        )
        self.assertEqual(post_resp.status_code, 403)


class AutoevaluacionYFirmaTests(CicloBaseTestCase):
    def test_guardar_borrador_y_enviar(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.client.force_login(self.empleado)
        borrador = self.client.post(
            reverse("evaluaciones:auto", args=[evaluacion.pk]),
            _formset_auto(evaluacion, puntaje=3, accion="borrador"),
        )
        self.assertEqual(borrador.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_BORRADOR)

        enviar = self.client.post(
            reverse("evaluaciones:auto", args=[evaluacion.pk]),
            _formset_auto(evaluacion, puntaje=4, comentario="Listo", accion="enviar"),
        )
        self.assertEqual(enviar.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_COMPLETA)
        self.assertIsNotNone(evaluacion.enviada_auto_en)

        otra = self.client.post(
            reverse("evaluaciones:auto", args=[evaluacion.pk]),
            _formset_auto(evaluacion, puntaje=1, accion="enviar"),
        )
        self.assertEqual(otra.status_code, 200)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_COMPLETA)
        self.assertEqual(evaluacion.respuestas.get().puntaje_empleado, 4)

    def test_comentario_obligatorio_al_enviar(self):
        self.criterio.comentario_empleado_obligatorio = True
        self.criterio.save(update_fields=["comentario_empleado_obligatorio"])
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        with self.assertRaises(EvaluacionesError):
            guardar_autoevaluacion(
                evaluacion,
                {
                    evaluacion.respuestas.get().pk: {
                        "puntaje_empleado": 4,
                        "comentario_empleado": "",
                    }
                },
                True,
                self.empleado,
            )

    def test_firma_genera_hash_estable_y_estado_final(self):
        from datetime import datetime

        from django.utils import timezone

        ts = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.get_current_timezone())
        h1 = calcular_firma_hash(10, 20, ts, [4, 5])
        h2 = calcular_firma_hash(10, 20, ts, [4, 5])
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
        self.assertNotEqual(h1, calcular_firma_hash(10, 20, ts, [3, 5]))

        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Bien"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Ok"}},
            "Muy buen desempeño",
            True,
            self.supervisor,
        )
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)

        firmar_conformidad(evaluacion, self.empleado, "127.0.0.1")
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA)
        self.assertEqual(len(evaluacion.firma_hash), 64)
        self.assertEqual(evaluacion.ip_firma, "127.0.0.1")
        self.assertIsNotNone(evaluacion.firmada_en)
        esperado = calcular_firma_hash(
            evaluacion.pk,
            self.empleado.pk,
            evaluacion.firmada_en,
            [evaluacion.respuestas.get().puntaje_supervisor],
        )
        self.assertEqual(evaluacion.firma_hash, esperado)

        with self.assertRaises(EvaluacionesError):
            guardar_eval_supervisor(
                evaluacion,
                {item.pk: {"puntaje_supervisor": 1, "comentario_supervisor": "x"}},
                "no",
                True,
                self.supervisor,
            )

    def test_observacion_deja_cerrada_con_obs(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 2, "comentario_empleado": "Regular"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Alto"}},
            "Feedback",
            True,
            self.supervisor,
        )
        self.client.force_login(self.empleado)
        response = self.client.post(
            reverse("evaluaciones:firmar", args=[evaluacion.pk]),
            {"accion": "observacion", "observacion": "No coincido con el puntaje."},
        )
        self.assertEqual(response.status_code, 302)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA_CON_OBS)
        self.assertIn("No coincido", evaluacion.comentario_empleado_cierre)
        resultado = self.client.get(
            reverse("evaluaciones:resultado", args=[evaluacion.pk])
        )
        self.assertContains(resultado, evaluacion.firma_hash)
        self.assertContains(resultado, "Comprobante de firma")

    def test_cerrar_supervisor_exige_feedback(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Ok"}},
            True,
            self.empleado,
        )
        with self.assertRaises(EvaluacionesError):
            guardar_eval_supervisor(
                evaluacion,
                {item.pk: {"puntaje_supervisor": 4, "comentario_supervisor": "Ok"}},
                "",
                True,
                self.supervisor,
            )


class PermisosRolTests(CicloBaseTestCase):
    def test_empleado_403_en_ciclos_y_equipo(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse("evaluaciones:ciclos")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("evaluaciones:ciclo_crear")).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse("evaluaciones:ciclo_detalle", args=[self.ciclo.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk])
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get(reverse("evaluaciones:equipo")).status_code, 403)
        self.assertEqual(
            self.client.get(
                reverse("evaluaciones:supervisar", args=[evaluacion.pk])
            ).status_code,
            403,
        )

    def test_supervisor_lee_ciclos_pero_no_activa(self):
        self.client.force_login(self.supervisor)
        self.assertEqual(self.client.get(reverse("evaluaciones:ciclos")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("evaluaciones:ciclo_crear")).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("evaluaciones:ciclo_activar", args=[self.ciclo.pk])
            ).status_code,
            403,
        )
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.estado, CicloEvaluacion.Estado.BORRADOR)

    def test_admin_rrhh_no_accede_a_equipo(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("evaluaciones:equipo")).status_code, 403)
