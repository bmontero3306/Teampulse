from decimal import Decimal

from django.utils import timezone

from app.tests.factories import (
    make_competencia,
    make_ciclo,
    make_empresa,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.models import CicloEvaluacion, Evaluacion, PlantillaCriterio
from evaluaciones.services import (
    activar_ciclo,
    agrupar_items_por_categoria,
    calcular_firma_hash,
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
    registrar_reunion_feedback,
)
from evaluaciones.tests.test_ciclos import CicloBaseTestCase, _criterio


def _respuestas(evaluacion, puntaje_field, comentario_field, puntaje, comentario):
    return [
        {
            "id": item.pk,
            puntaje_field: puntaje,
            comentario_field: comentario,
        }
        for item in evaluacion.respuestas.order_by("criterio__orden", "pk")
    ]


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

        self._auth(self.empleado)
        mias = self.client.get("/api/v1/evaluaciones/mias/")
        self.assertEqual(mias.status_code, 200)
        nombres = [item["ciclo_nombre"] for item in mias.data]
        self.assertIn("Ciclo Q1", nombres)
        self.assertNotIn(otro.email, mias.content.decode())

        propia = self.client.get(f"/api/v1/evaluaciones/{eval_propia.pk}/autoevaluacion/")
        self.assertEqual(propia.status_code, 200)
        ajena = self.client.get(f"/api/v1/evaluaciones/{eval_ajena.pk}/autoevaluacion/")
        self.assertEqual(ajena.status_code, 403)
        resultado_ajeno = self.client.get(f"/api/v1/evaluaciones/{eval_ajena.pk}/resultado/")
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

        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{eval_b.pk}/autoevaluacion/")
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

        self._auth(self.supervisor)
        get_resp = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/")
        self.assertEqual(get_resp.status_code, 403)
        post_resp = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/",
            {
                "cerrar": True,
                "habilitar_reunion": False,
                "feedback_supervisor": "Feedback",
                "respuestas": _respuestas(
                    evaluacion, "puntaje_supervisor", "comentario_supervisor", 5, "Bien"
                ),
            },
            format="json",
        )
        self.assertEqual(post_resp.status_code, 403)


class AutoevaluacionYFirmaTests(CicloBaseTestCase):
    def test_guardar_borrador_y_enviar(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self._auth(self.empleado)
        borrador = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": False,
                "respuestas": _respuestas(
                    evaluacion, "puntaje_empleado", "comentario_empleado", 3, "Ok"
                ),
            },
            format="json",
        )
        self.assertEqual(borrador.status_code, 200, borrador.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_BORRADOR)

        enviar = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": True,
                "respuestas": _respuestas(
                    evaluacion, "puntaje_empleado", "comentario_empleado", 4, "Listo"
                ),
            },
            format="json",
        )
        self.assertEqual(enviar.status_code, 200, enviar.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.AUTO_COMPLETA)
        self.assertIsNotNone(evaluacion.enviada_auto_en)

        otra = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": True,
                "respuestas": _respuestas(
                    evaluacion, "puntaje_empleado", "comentario_empleado", 1, "No"
                ),
            },
            format="json",
        )
        self.assertEqual(otra.status_code, 400)
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
        self._auth(self.empleado)
        response = self.client.post(
            f"/api/v1/evaluaciones/{evaluacion.pk}/firmar/",
            {"observacion": "No coincido con el puntaje."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA_CON_OBS)
        self.assertIn("No coincido", evaluacion.comentario_empleado_cierre)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertEqual(resultado.status_code, 200)
        self.assertEqual(resultado.data["firma_hash"], evaluacion.firma_hash)
        self.assertIn("No coincido", resultado.data["comentario_empleado_cierre"])

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
        self._auth(self.empleado)
        self.assertEqual(self.client.get("/api/v1/ciclos/").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/ciclos/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/ciclos/{self.ciclo.pk}/").status_code, 403)
        self.assertEqual(
            self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/").status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/evaluaciones/equipo/").status_code, 403)
        self.assertEqual(
            self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/").status_code,
            403,
        )

    def test_supervisor_lee_ciclos_pero_no_activa(self):
        self._auth(self.supervisor)
        self.assertEqual(self.client.get("/api/v1/ciclos/").status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/v1/ciclos/",
                {"nombre": "No"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/ciclos/{self.ciclo.pk}/activar/").status_code,
            403,
        )
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.estado, CicloEvaluacion.Estado.BORRADOR)

    def test_supervisor_no_crea_plantillas(self):
        self._auth(self.supervisor)
        response = self.client.post(
            "/api/v1/plantillas/",
            {"nombre": "No", "tipo": "mixta", "criterios": []},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_rrhh_no_accede_a_equipo(self):
        self._auth(self.admin)
        self.assertEqual(self.client.get("/api/v1/evaluaciones/equipo/").status_code, 403)


class FlujoCiego180Tests(CicloBaseTestCase):
    def _avanzar_hasta_comparacion(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Listo ciego"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Ok jefe"}},
            "Feedback independiente",
            True,
            self.supervisor,
            habilitar_reunion=True,
        )
        evaluacion.refresh_from_db()
        return evaluacion

    def test_supervisor_no_ve_autoevaluacion_en_supervisar(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Listo ciego"}},
            True,
            self.empleado,
        )
        self._auth(self.supervisor)
        response = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/")
        self.assertEqual(response.status_code, 200, response.content)
        cuerpo = response.content.decode()
        self.assertNotIn("Listo ciego", cuerpo)
        self.assertIsNone(response.data["respuestas"][0]["puntaje_empleado"])
        self.assertEqual(response.data["respuestas"][0]["comentario_empleado"], "")

    def test_cerrar_jefe_revela_comparacion_con_brecha(self):
        evaluacion = self._avanzar_hasta_comparacion()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_COMPARACION)
        self.assertEqual(evaluacion.respuestas.get().brecha, 1)
        self.assertEqual(evaluacion.respuestas.get().brecha_display, "+1")

        self._auth(self.empleado)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertEqual(resultado.status_code, 200)
        item = resultado.data["respuestas"][0]
        self.assertEqual(item["comentario_empleado"], "Listo ciego")
        self.assertEqual(item["comentario_supervisor"], "Ok jefe")
        self.assertEqual(item["brecha"], 1)
        self.assertFalse(resultado.data["puede_firmar"])
        self.assertFalse(resultado.data["puede_reunion"])

    def test_supervisor_y_rrhh_ven_resultado_tercero_no(self):
        evaluacion = self._avanzar_hasta_comparacion()
        self._auth(self.supervisor)
        self.assertEqual(
            self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/").status_code,
            200,
        )
        self._auth(self.admin)
        self.assertEqual(
            self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/").status_code,
            200,
        )
        tercero = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            area=self.area,
            supervisor=self.supervisor,
            first_name="Otro",
            last_name="Empleado",
        )
        self._auth(tercero)
        self.assertEqual(
            self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/").status_code,
            403,
        )

    def test_registrar_reunion_habilita_firma(self):
        evaluacion = self._avanzar_hasta_comparacion()
        self._auth(self.supervisor)
        response = self.client.post(
            f"/api/v1/evaluaciones/{evaluacion.pk}/reunion/",
            {
                "reunion_fecha": timezone.now().isoformat(),
                "reunion_notas": "Hablamos las brechas.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)
        self.assertIn("brechas", evaluacion.reunion_notas)

        self._auth(self.empleado)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertTrue(resultado.data["puede_firmar"])
        self.assertIn("Hablamos las brechas.", resultado.data["reunion_notas"])

    def test_habilitar_reunion_por_api(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Ok"}},
            True,
            self.empleado,
        )
        self._auth(self.supervisor)
        response = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/",
            {
                "cerrar": True,
                "habilitar_reunion": True,
                "feedback_supervisor": "Feedback",
                "respuestas": _respuestas(
                    evaluacion, "puntaje_supervisor", "comentario_supervisor", 5, "Bien"
                ),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_COMPARACION)

    def test_cerrar_sin_reunion_habilita_firma(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Ok"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Bien"}},
            "Feedback por sistema",
            True,
            self.supervisor,
        )
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)
        self._auth(self.empleado)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertTrue(resultado.data["puede_firmar"])
        self.assertEqual(resultado.data["feedback_supervisor"], "Feedback por sistema")
        self.assertFalse((resultado.data["reunion_notas"] or "").strip())

    def test_omitir_reunion_habilita_firma(self):
        evaluacion = self._avanzar_hasta_comparacion()
        with self.assertRaises(EvaluacionesError):
            firmar_conformidad(evaluacion, self.empleado, "127.0.0.1")
        self._auth(self.supervisor)
        response = self.client.post(f"/api/v1/evaluaciones/{evaluacion.pk}/omitir-reunion/")
        self.assertEqual(response.status_code, 200, response.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)
        self.assertFalse((evaluacion.reunion_notas or "").strip())
        self._auth(self.empleado)
        resultado = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado/")
        self.assertTrue(resultado.data["puede_firmar"])
        self.assertFalse((resultado.data["reunion_notas"] or "").strip())


class ResultadoPdfTests(CicloBaseTestCase):
    def _avanzar_hasta_comparacion(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Listo ciego"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Ok jefe"}},
            "Feedback independiente",
            True,
            self.supervisor,
            habilitar_reunion=True,
        )
        evaluacion.refresh_from_db()
        return evaluacion

    def test_pdf_propio_200_y_content_type(self):
        from evaluaciones.pdf import CONTENT_TYPE_PDF, nombre_archivo_pdf, numero_documento

        evaluacion = self._avanzar_hasta_comparacion()
        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_PDF)
        self.assertTrue(response.content.startswith(b"%PDF"), "La respuesta no es un PDF")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertIn(nombre_archivo_pdf(evaluacion), response["Content-Disposition"])
        cuerpo = response.content
        self.assertIn(numero_documento(evaluacion).encode("ascii"), cuerpo)
        self.assertIn(b"TeamPulse", cuerpo)
        self.assertIn(b"Listo ciego", cuerpo)
        self.assertIn(b"Ok jefe", cuerpo)
        self.assertIn(b"FIRMA DIGITAL", cuerpo)

    def test_pdf_oculta_supervisor_antes_de_comparacion(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        item = evaluacion.respuestas.get()
        guardar_autoevaluacion(
            evaluacion,
            {item.pk: {"puntaje_empleado": 4, "comentario_empleado": "Listo ciego"}},
            True,
            self.empleado,
        )
        guardar_eval_supervisor(
            evaluacion,
            {item.pk: {"puntaje_supervisor": 5, "comentario_supervisor": "Ok jefe"}},
            "Feedback oculto",
            False,
            self.supervisor,
        )
        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        self.assertEqual(response.status_code, 200)
        cuerpo = response.content
        self.assertIn(b"Listo ciego", cuerpo)
        self.assertNotIn(b"Ok jefe", cuerpo)
        self.assertIn(b"PENDIENTE DE FIRMA DIGITAL", cuerpo)

    def test_pdf_incluye_hash_cuando_esta_firmada(self):
        evaluacion = self._avanzar_hasta_comparacion()
        registrar_reunion_feedback(
            evaluacion,
            timezone.now(),
            "Reunion PDF.",
            self.supervisor,
        )
        firmar_conformidad(evaluacion, self.empleado, "127.0.0.1")
        evaluacion.refresh_from_db()
        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        self.assertEqual(response.status_code, 200)
        cuerpo = response.content
        self.assertIn(evaluacion.firma_hash.encode("ascii"), cuerpo)
        self.assertIn(b"SHA-256", cuerpo)

    def test_pdf_registra_auditoria(self):
        from auditoria.constants import Accion
        from auditoria.models import AuditLog

        evaluacion = self._avanzar_hasta_comparacion()
        self._auth(self.empleado)
        self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        log = AuditLog.objects.filter(
            accion=Accion.EXPORTAR,
            object_id=str(evaluacion.pk),
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.payload.get("formato"), "pdf")
        self.assertEqual(log.payload.get("tipo"), "resultado_evaluacion")

    def test_tercero_no_descarga_pdf(self):
        evaluacion = self._avanzar_hasta_comparacion()
        tercero = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            area=self.area,
            supervisor=self.supervisor,
            first_name="Otro",
            last_name="Empleado",
        )
        self._auth(tercero)
        self.assertEqual(
            self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf").status_code,
            403,
        )

    def test_tenant_no_descarga_pdf_ajeno(self):
        empresa_b = make_empresa()
        puesto_b = make_puesto(empresa_b)
        empleado_b = make_usuario(empresa_b, rol="empleado", puesto=puesto_b)
        plantilla_b = make_plantilla(empresa_b)
        _criterio(plantilla_b, make_competencia(empresa_b))
        ciclo_b = make_ciclo(empresa_b, plantilla_default=plantilla_b)
        admin_b = make_usuario(empresa_b, rol="admin_rrhh")
        activar_ciclo(ciclo_b, admin_b)
        eval_b = Evaluacion.objects.get(ciclo=ciclo_b, evaluado=empleado_b)

        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{eval_b.pk}/resultado.pdf")
        self.assertEqual(response.status_code, 404)


class ItemTextoYCategoriaTests(CicloBaseTestCase):
    def setUp(self):
        super().setUp()
        self.criterio.categoria = "Competencias generales"
        self.criterio.save(update_fields=["categoria"])
        self.comp_texto = make_competencia(self.empresa, nombre="Fortalezas destacadas")
        self.criterio_texto = _criterio(
            self.plantilla,
            self.comp_texto,
            orden=2,
            categoria="Cierre",
            tipo_item=PlantillaCriterio.TipoItem.TEXTO,
            ponderacion=Decimal("0"),
            comentario_empleado_obligatorio=True,
            comentario_supervisor_obligatorio=True,
        )

    def _items(self, evaluacion):
        return {item.criterio_id: item for item in evaluacion.respuestas.all()}

    def test_enviar_auto_texto_sin_puntaje(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        items = self._items(evaluacion)
        guardar_autoevaluacion(
            evaluacion,
            {
                items[self.criterio.pk].pk: {
                    "puntaje_empleado": 4,
                    "comentario_empleado": "Ok",
                },
                items[self.criterio_texto.pk].pk: {
                    "puntaje_empleado": 3,
                    "comentario_empleado": "Buena autonomía",
                },
            },
            True,
            self.empleado,
        )
        texto = evaluacion.respuestas.get(criterio=self.criterio_texto)
        self.assertIsNone(texto.puntaje_empleado)
        self.assertEqual(texto.comentario_empleado, "Buena autonomía")

    def test_enviar_auto_texto_sin_devolucion_falla(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        items = self._items(evaluacion)
        with self.assertRaises(EvaluacionesError):
            guardar_autoevaluacion(
                evaluacion,
                {
                    items[self.criterio.pk].pk: {
                        "puntaje_empleado": 4,
                        "comentario_empleado": "Ok",
                    },
                    items[self.criterio_texto.pk].pk: {
                        "puntaje_empleado": None,
                        "comentario_empleado": "",
                    },
                },
                True,
                self.empleado,
            )

    def test_autoevaluacion_expone_categorias_y_tipo(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        self._auth(self.empleado)
        response = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/")
        self.assertEqual(response.status_code, 200)
        por_nombre = {item["competencia"]: item for item in response.data["respuestas"]}
        self.assertEqual(por_nombre["Comunicación"]["categoria"], "Competencias generales")
        self.assertEqual(por_nombre["Fortalezas destacadas"]["categoria"], "Cierre")
        self.assertEqual(por_nombre["Fortalezas destacadas"]["tipo_item"], "texto")
        self.assertTrue(por_nombre["Fortalezas destacadas"]["comentario_empleado_obligatorio"])

    def test_agrupar_items_por_categoria(self):
        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        grupos = agrupar_items_por_categoria(
            evaluacion.respuestas.order_by("criterio__orden", "pk")
        )
        self.assertEqual(
            [g["nombre"] for g in grupos], ["Competencias generales", "Cierre"]
        )
        self.assertEqual(len(grupos[0]["items"]), 1)
        self.assertEqual(len(grupos[1]["items"]), 1)

    def test_promedio_ignora_item_texto(self):
        from evaluaciones.pdf import _promedio_ponderado

        activar_ciclo(self.ciclo, self.admin)
        evaluacion = Evaluacion.objects.get(ciclo=self.ciclo, evaluado=self.empleado)
        items = self._items(evaluacion)
        guardar_autoevaluacion(
            evaluacion,
            {
                items[self.criterio.pk].pk: {
                    "puntaje_empleado": 4,
                    "comentario_empleado": "Ok",
                },
                items[self.criterio_texto.pk].pk: {
                    "puntaje_empleado": None,
                    "comentario_empleado": "Texto",
                },
            },
            True,
            self.empleado,
        )
        evaluacion.refresh_from_db()
        promedio = _promedio_ponderado(
            list(evaluacion.respuestas.select_related("criterio")),
            "puntaje_empleado",
        )
        self.assertEqual(promedio, Decimal("4.00"))
