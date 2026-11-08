from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import (
    make_competencia,
    make_empresa,
    make_puesto,
    make_usuario,
)
from evaluaciones.models import (
    PlantillaCriterio,
    PlantillaEvaluacion,
    PlantillaPuesto,
)
from evaluaciones.services import duplicar_plantilla


def _auth(client, usuario):
    token, _ = Token.objects.get_or_create(user=usuario)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


def _payload(competencia, **extra):
    datos = {
        "nombre": "Plantilla técnica",
        "tipo": PlantillaEvaluacion.Tipo.TECNICA,
        "descripcion": "",
        "activa": True,
        "puestos": [],
        "criterios": [
            {
                "competencia": competencia.pk,
                "categoria": "",
                "tipo_item": "escala",
                "orden": 1,
                "escala_min": 1,
                "escala_max": 5,
                "ponderacion": "100",
                "comentario_empleado_obligatorio": True,
                "comentario_supervisor_obligatorio": True,
            }
        ],
    }
    datos.update(extra)
    return datos


class DuplicarPlantillaTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.competencia = make_competencia(self.empresa, nombre="Comunicación")
        self.puesto = make_puesto(self.empresa, nombre="Analista")
        self.plantilla = PlantillaEvaluacion.objects.create(
            empresa=self.empresa,
            nombre="Evaluación anual",
            tipo=PlantillaEvaluacion.Tipo.MIXTA,
            descripcion="Original",
            activa=True,
        )
        self.criterio = PlantillaCriterio.objects.create(
            plantilla=self.plantilla,
            competencia=self.competencia,
            categoria="Competencias generales",
            tipo_item=PlantillaCriterio.TipoItem.ESCALA,
            orden=1,
            escala_min=1,
            escala_max=5,
            ponderacion=Decimal("40.00"),
            comentario_empleado_obligatorio=True,
        )
        PlantillaPuesto.objects.create(plantilla=self.plantilla, puesto=self.puesto)

    def test_duplicar_copia_criterios_y_no_comparte_pk(self):
        copia = duplicar_plantilla(self.plantilla)
        self.assertNotEqual(copia.pk, self.plantilla.pk)
        self.assertEqual(copia.nombre, "Copia de Evaluación anual")
        self.assertEqual(copia.duplicada_desde_id, self.plantilla.pk)
        self.assertEqual(copia.tipo, self.plantilla.tipo)
        self.assertEqual(copia.descripcion, self.plantilla.descripcion)

        criterios_copia = list(copia.criterios.order_by("orden"))
        self.assertEqual(len(criterios_copia), 1)
        criterio_copia = criterios_copia[0]
        self.assertNotEqual(criterio_copia.pk, self.criterio.pk)
        self.assertEqual(criterio_copia.competencia_id, self.competencia.pk)
        self.assertEqual(criterio_copia.ponderacion, Decimal("40.00"))
        self.assertEqual(criterio_copia.categoria, "Competencias generales")
        self.assertEqual(criterio_copia.tipo_item, PlantillaCriterio.TipoItem.ESCALA)
        self.assertTrue(criterio_copia.comentario_empleado_obligatorio)
        self.assertEqual(
            list(copia.puestos.values_list("pk", flat=True)),
            [self.puesto.pk],
        )
        self.assertTrue(
            PlantillaEvaluacion.objects.filter(pk=self.plantilla.pk).exists()
        )
        self.assertEqual(self.plantilla.criterios.count(), 1)


class PlantillaPuestoTenantTests(APITestCase):
    def setUp(self):
        self.empresa_a = make_empresa()
        self.empresa_b = make_empresa()
        self.plantilla_a = PlantillaEvaluacion.objects.create(
            empresa=self.empresa_a,
            nombre="Plantilla A",
            tipo=PlantillaEvaluacion.Tipo.TECNICA,
        )
        self.puesto_a = make_puesto(self.empresa_a, nombre="Puesto A")
        self.puesto_b = make_puesto(self.empresa_b, nombre="Puesto B")

    def test_no_asociar_puesto_de_otra_empresa(self):
        vinculo = PlantillaPuesto(
            plantilla=self.plantilla_a,
            puesto=self.puesto_b,
        )
        with self.assertRaises(ValidationError):
            vinculo.full_clean()

    def test_asociar_puesto_misma_empresa(self):
        vinculo = PlantillaPuesto(
            plantilla=self.plantilla_a,
            puesto=self.puesto_a,
        )
        vinculo.full_clean()
        vinculo.save()
        self.assertTrue(
            PlantillaPuesto.objects.filter(
                plantilla=self.plantilla_a, puesto=self.puesto_a
            ).exists()
        )

    def test_api_no_asocia_puesto_de_otra_empresa(self):
        admin = make_usuario(self.empresa_a, rol="admin_rrhh")
        competencia = make_competencia(self.empresa_a)
        _auth(self.client, admin)
        response = self.client.post(
            "/api/v1/plantillas/",
            _payload(competencia, puestos=[self.puesto_b.pk]),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(PlantillaPuesto.objects.filter(puesto=self.puesto_b).exists())
        self.assertFalse(
            PlantillaEvaluacion.objects.filter(nombre="Plantilla técnica").exists()
        )


class PlantillaValidacionTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.competencia = make_competencia(self.empresa)
        self.plantilla = PlantillaEvaluacion.objects.create(
            empresa=self.empresa,
            nombre="Plantilla",
            tipo=PlantillaEvaluacion.Tipo.MIXTA,
        )

    def test_escala_min_debe_ser_menor_que_max(self):
        criterio = PlantillaCriterio(
            plantilla=self.plantilla,
            competencia=self.competencia,
            orden=1,
            escala_min=5,
            escala_max=5,
            ponderacion=Decimal("10"),
        )
        with self.assertRaises(ValidationError):
            criterio.full_clean()

    def test_ponderacion_no_negativa(self):
        criterio = PlantillaCriterio(
            plantilla=self.plantilla,
            competencia=self.competencia,
            orden=1,
            escala_min=1,
            escala_max=5,
            ponderacion=Decimal("-1"),
        )
        with self.assertRaises(ValidationError):
            criterio.full_clean()

    def test_item_texto_no_exige_escala_y_pondera_cero(self):
        criterio = PlantillaCriterio(
            plantilla=self.plantilla,
            competencia=self.competencia,
            categoria="Cierre",
            tipo_item=PlantillaCriterio.TipoItem.TEXTO,
            orden=1,
            escala_min=5,
            escala_max=5,
            ponderacion=Decimal("20"),
        )
        criterio.full_clean()
        self.assertEqual(criterio.ponderacion, Decimal("0"))
        self.assertTrue(criterio.es_texto)

    def test_api_rechaza_escala_invertida(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        _auth(self.client, admin)
        criterios = _payload(self.competencia)["criterios"]
        criterios[0]["escala_min"] = 5
        criterios[0]["escala_max"] = 5
        response = self.client.post(
            "/api/v1/plantillas/",
            _payload(self.competencia, criterios=criterios),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("menor que la máxima", response.content.decode())

    def test_api_rechaza_competencia_repetida(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        _auth(self.client, admin)
        fila = _payload(self.competencia)["criterios"][0]
        response = self.client.post(
            "/api/v1/plantillas/",
            _payload(self.competencia, criterios=[fila, {**fila, "orden": 2}]),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("misma competencia", response.content.decode())

    def test_api_crea_criterio_solo_texto(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        _auth(self.client, admin)
        criterios = _payload(self.competencia)["criterios"]
        criterios[0]["categoria"] = "Cierre"
        criterios[0]["tipo_item"] = "texto"
        criterios[0]["ponderacion"] = "15"
        response = self.client.post(
            "/api/v1/plantillas/",
            _payload(self.competencia, criterios=criterios),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        criterio = PlantillaCriterio.objects.get(competencia=self.competencia, categoria="Cierre")
        self.assertEqual(criterio.tipo_item, PlantillaCriterio.TipoItem.TEXTO)
        self.assertEqual(criterio.categoria, "Cierre")
        self.assertEqual(criterio.ponderacion, Decimal("0"))
        self.assertTrue(criterio.comentario_empleado_obligatorio)
        self.assertTrue(criterio.comentario_supervisor_obligatorio)


class PlantillaPermisosTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.plantilla = PlantillaEvaluacion.objects.create(
            empresa=self.empresa,
            nombre="Visible",
            tipo=PlantillaEvaluacion.Tipo.MIXTA,
        )

    def test_empleado_no_accede(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        _auth(self.client, empleado)
        response = self.client.get("/api/v1/plantillas/")
        self.assertEqual(response.status_code, 403)

    def test_supervisor_lee_y_no_crea(self):
        supervisor = make_usuario(self.empresa, rol="supervisor")
        _auth(self.client, supervisor)
        lista = self.client.get("/api/v1/plantillas/")
        self.assertEqual(lista.status_code, 200)
        nombres = [item["nombre"] for item in lista.data["results"]]
        self.assertIn("Visible", nombres)
        crear = self.client.post(
            "/api/v1/plantillas/",
            _payload(make_competencia(self.empresa)),
            format="json",
        )
        self.assertEqual(crear.status_code, 403)
        duplicar = self.client.post(f"/api/v1/plantillas/{self.plantilla.pk}/duplicar/")
        self.assertEqual(duplicar.status_code, 403)
        self.assertEqual(PlantillaEvaluacion.objects.filter(duplicada_desde=self.plantilla).count(), 0)

    def test_admin_rrhh_crud(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        competencia = make_competencia(self.empresa)
        puesto = make_puesto(self.empresa, nombre="Analista")
        _auth(self.client, admin)
        lista = self.client.get("/api/v1/plantillas/")
        self.assertEqual(lista.status_code, 200)
        response = self.client.post(
            "/api/v1/plantillas/",
            _payload(competencia, puestos=[puesto.pk]),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        plantilla = PlantillaEvaluacion.objects.get(nombre="Plantilla técnica")
        self.assertEqual(list(plantilla.puestos.all()), [puesto])
        self.assertEqual(response.data["criterios"][0]["categoria"], "")

    def test_listado_filtra_por_empresa(self):
        otra = make_empresa()
        PlantillaEvaluacion.objects.create(
            empresa=otra,
            nombre="Ajena",
            tipo=PlantillaEvaluacion.Tipo.TECNICA,
        )
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        _auth(self.client, admin)
        response = self.client.get("/api/v1/plantillas/")
        nombres = [item["nombre"] for item in response.data["results"]]
        self.assertIn("Visible", nombres)
        self.assertNotIn("Ajena", nombres)
