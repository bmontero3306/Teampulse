from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_competencia, make_empresa, make_puesto, make_usuario
from cuentas.models import Usuario
from evaluaciones.models import CicloEvaluacion, Evaluacion, PlantillaEvaluacion
from organizacion.models import Area


class ApiFlujoTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.password = "clave-test-123"
        self.admin = make_usuario(self.empresa, rol="admin_rrhh", password=self.password)
        self.area = Area.objects.create(empresa=self.empresa, nombre="Operaciones")
        self.puesto = make_puesto(self.empresa, area=self.area)
        self.supervisor = make_usuario(
            self.empresa,
            rol="supervisor",
            puesto=self.puesto,
            area=self.area,
            password=self.password,
        )
        self.empleado = make_usuario(
            self.empresa,
            rol="empleado",
            puesto=self.puesto,
            area=self.area,
            supervisor=self.supervisor,
            password=self.password,
        )
        self._auth(self.admin)

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_plantilla_ciclo_auto_supervisor_y_firma(self):
        competencia = make_competencia(self.empresa)
        plantilla = self.client.post(
            "/api/v1/plantillas/",
            {
                "nombre": "Desempeño",
                "tipo": "mixta",
                "descripcion": "",
                "activa": True,
                "puestos": [self.puesto.pk],
                "criterios": [
                    {
                        "competencia": competencia.pk,
                        "categoria": "General",
                        "tipo_item": "escala",
                        "orden": 1,
                        "escala_min": 1,
                        "escala_max": 5,
                        "ponderacion": "100.00",
                        "comentario_empleado_obligatorio": True,
                        "comentario_supervisor_obligatorio": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(plantilla.status_code, 201, plantilla.content)
        ciclo = self.client.post(
            "/api/v1/ciclos/",
            {
                "nombre": "Ciclo API",
                "fecha_inicio": "2026-01-01",
                "fecha_cierre": "2026-12-31",
                "plantilla_default": plantilla.data["id"],
                "areas": [],
                "criterios_generales": "",
            },
            format="json",
        )
        self.assertEqual(ciclo.status_code, 201, ciclo.content)
        activado = self.client.post(f"/api/v1/ciclos/{ciclo.data['id']}/activar/")
        self.assertEqual(activado.status_code, 200, activado.content)
        self.assertEqual(activado.data["estado"], CicloEvaluacion.Estado.ACTIVO)

        evaluacion = Evaluacion.objects.get(ciclo_id=ciclo.data["id"], evaluado=self.empleado)
        self._auth(self.empleado)
        item = evaluacion.respuestas.get()
        borrador = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": False,
                "respuestas": [{"id": item.pk, "puntaje_empleado": 3, "comentario_empleado": ""}],
            },
            format="json",
        )
        self.assertEqual(borrador.status_code, 200, borrador.content)
        enviado = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/autoevaluacion/",
            {
                "enviar": True,
                "respuestas": [
                    {"id": item.pk, "puntaje_empleado": 4, "comentario_empleado": "Listo"}
                ],
            },
            format="json",
        )
        self.assertEqual(enviado.status_code, 200, enviado.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.SUPERVISOR)

        self._auth(self.supervisor)
        cerrado = self.client.put(
            f"/api/v1/evaluaciones/{evaluacion.pk}/supervisar/",
            {
                "cerrar": True,
                "habilitar_reunion": False,
                "feedback_supervisor": "Buen trabajo",
                "respuestas": [
                    {
                        "id": item.pk,
                        "puntaje_supervisor": 4,
                        "comentario_supervisor": "De acuerdo",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(cerrado.status_code, 200, cerrado.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.PENDIENTE_CONFORMIDAD)

        self._auth(self.empleado)
        firma = self.client.post(
            f"/api/v1/evaluaciones/{evaluacion.pk}/firmar/",
            {"observacion": ""},
            format="json",
        )
        self.assertEqual(firma.status_code, 200, firma.content)
        evaluacion.refresh_from_db()
        self.assertEqual(evaluacion.estado, Evaluacion.Estado.CERRADA)
        self.assertTrue(evaluacion.firma_hash)

        pdf = self.client.get(f"/api/v1/evaluaciones/{evaluacion.pk}/resultado.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")

        self._auth(self.admin)
        panel = self.client.get("/api/v1/dashboard/")
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.data["kpis"]["firmadas"], 1)
        self.assertTrue(PlantillaEvaluacion.objects.filter(pk=plantilla.data["id"]).exists())

    def test_empleado_no_lista_usuarios(self):
        self._auth(self.empleado)
        response = self.client.get("/api/v1/usuarios/")
        self.assertEqual(response.status_code, 403)

    def test_superadmin_sin_empresa_no_crea_area(self):
        superadmin = Usuario.objects.create_superuser(
            email="superapi@teampulse.test",
            password=self.password,
        )
        self._auth(superadmin)
        response = self.client.post("/api/v1/areas/", {"nombre": "Nueva"}, format="json")
        self.assertEqual(response.status_code, 403)
