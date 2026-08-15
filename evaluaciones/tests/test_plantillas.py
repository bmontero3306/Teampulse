from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

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


def _datos_formset(competencia, extra=None):
    datos = {
        "nombre": "Plantilla técnica",
        "tipo": PlantillaEvaluacion.Tipo.TECNICA,
        "descripcion": "",
        "activa": "on",
        "criterios-TOTAL_FORMS": "1",
        "criterios-INITIAL_FORMS": "0",
        "criterios-MIN_NUM_FORMS": "0",
        "criterios-MAX_NUM_FORMS": "1000",
        "criterios-0-competencia": str(competencia.pk),
        "criterios-0-categoria": "",
        "criterios-0-tipo_item": "escala",
        "criterios-0-orden": "1",
        "criterios-0-escala_min": "1",
        "criterios-0-escala_max": "5",
        "criterios-0-ponderacion": "100",
    }
    if extra:
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


class PlantillaPuestoTenantTests(TestCase):
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

    def test_vista_no_asocia_puesto_de_otra_empresa(self):
        admin = make_usuario(self.empresa_a, rol="admin_rrhh")
        competencia = make_competencia(self.empresa_a)
        self.client.force_login(admin)
        datos = _datos_formset(
            competencia,
            extra={"puestos": [str(self.puesto_b.pk)]},
        )
        response = self.client.post(reverse("evaluaciones:plantilla_crear"), datos)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            PlantillaPuesto.objects.filter(puesto=self.puesto_b).exists()
        )
        self.assertFalse(
            PlantillaEvaluacion.objects.filter(nombre="Plantilla técnica").exists()
        )


class PlantillaValidacionTests(TestCase):
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

    def test_vista_crea_criterio_solo_texto(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.client.force_login(admin)
        datos = _datos_formset(
            self.competencia,
            extra={
                "criterios-0-categoria": "Cierre",
                "criterios-0-tipo_item": "texto",
                "criterios-0-ponderacion": "15",
            },
        )
        response = self.client.post(reverse("evaluaciones:plantilla_crear"), datos)
        self.assertEqual(response.status_code, 302)
        criterio = PlantillaCriterio.objects.get(competencia=self.competencia)
        self.assertEqual(criterio.tipo_item, PlantillaCriterio.TipoItem.TEXTO)
        self.assertEqual(criterio.categoria, "Cierre")
        self.assertEqual(criterio.ponderacion, Decimal("0"))


class PlantillaPermisosTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.plantilla = PlantillaEvaluacion.objects.create(
            empresa=self.empresa,
            nombre="Visible",
            tipo=PlantillaEvaluacion.Tipo.MIXTA,
        )

    def test_empleado_no_accede(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        self.client.force_login(empleado)
        response = self.client.get(reverse("evaluaciones:plantillas"))
        self.assertEqual(response.status_code, 403)

    def test_supervisor_lee_y_no_crea(self):
        supervisor = make_usuario(self.empresa, rol="supervisor")
        self.client.force_login(supervisor)
        lista = self.client.get(reverse("evaluaciones:plantillas"))
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, "Visible")
        self.assertNotContains(lista, "Nueva plantilla")
        crear = self.client.get(reverse("evaluaciones:plantilla_crear"))
        self.assertEqual(crear.status_code, 403)
        duplicar = self.client.post(
            reverse("evaluaciones:plantilla_duplicar", args=[self.plantilla.pk])
        )
        self.assertEqual(duplicar.status_code, 403)

    def test_admin_rrhh_crud(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        competencia = make_competencia(self.empresa)
        self.client.force_login(admin)
        lista = self.client.get(reverse("evaluaciones:plantillas"))
        self.assertEqual(lista.status_code, 200)
        crear = self.client.get(reverse("evaluaciones:plantilla_crear"))
        self.assertEqual(crear.status_code, 200)
        response = self.client.post(
            reverse("evaluaciones:plantilla_crear"),
            _datos_formset(competencia),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PlantillaEvaluacion.objects.filter(nombre="Plantilla técnica").exists()
        )

    def test_listado_filtra_por_empresa(self):
        otra = make_empresa()
        PlantillaEvaluacion.objects.create(
            empresa=otra,
            nombre="Ajena",
            tipo=PlantillaEvaluacion.Tipo.TECNICA,
        )
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.client.force_login(admin)
        response = self.client.get(reverse("evaluaciones:plantillas"))
        self.assertContains(response, "Visible")
        self.assertNotContains(response, "Ajena")


class PlantillaFormularioUXTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.competencia = make_competencia(self.empresa, nombre="Comunicación")
        self.puesto = make_puesto(self.empresa, nombre="Analista")
        self.client.force_login(self.admin)

    def test_formulario_tiene_buscador_de_puestos_y_labels_claros(self):
        response = self.client.get(reverse("evaluaciones:plantilla_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buscar puesto")
        self.assertContains(response, "Analista")
        self.assertContains(response, "Agregar criterio")
        self.assertContains(response, "Editar")
        self.assertContains(response, "Devolución del empleado obligatoria")
        self.assertContains(response, "Devolución del supervisor obligatoria")
        self.assertContains(response, "Quitar de la plantilla")
        self.assertContains(response, "Crear una competencia nueva")
        self.assertNotContains(response, "Dev. emp.")
        self.assertNotContains(response, "Ctrl o Cmd")

    def test_asocia_puestos_de_la_empresa(self):
        response = self.client.post(
            reverse("evaluaciones:plantilla_crear"),
            _datos_formset(
                self.competencia,
                extra={"puestos": [str(self.puesto.pk)]},
            ),
        )
        self.assertEqual(response.status_code, 302)
        plantilla = PlantillaEvaluacion.objects.get(nombre="Plantilla técnica")
        self.assertEqual(list(plantilla.puestos.all()), [self.puesto])
