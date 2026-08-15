from django.test import TestCase
from django.urls import reverse

from app.tests.factories import (
    make_area,
    make_competencia,
    make_empresa,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from evaluaciones.models import PlantillaPuesto
from organizacion.models import Competencia, Puesto


class VistasOrganizacionTests(TestCase):
    def setUp(self):
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.admin_a = make_usuario(self.empresa_a, rol="admin_rrhh")
        self.admin_b = make_usuario(self.empresa_b, rol="admin_rrhh")
        self.supervisor_a = make_usuario(self.empresa_a, rol="supervisor")
        self.empleado_a = make_usuario(self.empresa_a, rol="empleado")

    def test_listado_puestos_filtrado_por_tenant(self):
        make_puesto(self.empresa_a, nombre="De A")
        make_puesto(self.empresa_b, nombre="De B")
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("organizacion:puestos"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "De A")
        self.assertNotContains(response, "De B")

    def test_listado_areas_filtrado_por_tenant(self):
        make_area(self.empresa_a, nombre="Área De A")
        make_area(self.empresa_b, nombre="Área De B")
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("organizacion:areas"))
        self.assertContains(response, "Área De A")
        self.assertNotContains(response, "Área De B")

    def test_listado_competencias_filtrado_por_tenant(self):
        make_competencia(self.empresa_a, nombre="Comp De A")
        make_competencia(self.empresa_b, nombre="Comp De B")
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("organizacion:competencias"))
        self.assertContains(response, "Comp De A")
        self.assertNotContains(response, "Comp De B")

    def test_organigrama_filtrado_por_tenant(self):
        make_puesto(self.empresa_a, nombre="Raíz A")
        make_puesto(self.empresa_b, nombre="Raíz B")
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("organizacion:organigrama"))
        self.assertContains(response, "Raíz A")
        self.assertNotContains(response, "Raíz B")

    def test_organigrama_nodos_colapsados_por_defecto(self):
        raiz = make_puesto(self.empresa_a, nombre="Director")
        make_puesto(self.empresa_a, nombre="Analista", puesto_superior=raiz)
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("organizacion:organigrama"))
        self.assertContains(response, "Expandir todo")
        self.assertContains(response, "Colapsar todo")
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, f'id="org-hijos-{raiz.pk}"')
        self.assertContains(response, "Analista")
        self.assertContains(response, "1 puesto a cargo")

    def test_referencia_circular_visible_en_form(self):
        gerente = make_puesto(self.empresa_a, nombre="Gerente")
        jefe = make_puesto(self.empresa_a, nombre="Jefe", puesto_superior=gerente)
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("organizacion:puesto_editar", args=[gerente.pk]),
            {
                "nombre": "Gerente",
                "descripcion": "",
                "area": "",
                "puesto_superior": str(jefe.pk),
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "circular")
        gerente.refresh_from_db()
        self.assertIsNone(gerente.puesto_superior_id)

    def test_formulario_puesto_no_pide_competencias(self):
        puesto = make_puesto(self.empresa_a, nombre="Analista")
        plantilla = make_plantilla(self.empresa_a, nombre="Plantilla Analista")
        PlantillaPuesto.objects.create(plantilla=plantilla, puesto=puesto)
        self.client.force_login(self.admin_a)
        response = self.client.get(
            reverse("organizacion:puesto_editar", args=[puesto.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Competencias y ponderación")
        self.assertContains(response, "plantilla por defecto del ciclo")
        self.assertContains(response, "Plantilla Analista")

    def test_supervisor_lee_pero_no_crea(self):
        make_puesto(self.empresa_a, nombre="Visible")
        self.client.force_login(self.supervisor_a)
        self.assertEqual(
            self.client.get(reverse("organizacion:puestos")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("organizacion:puesto_crear")).status_code, 403
        )

    def test_empleado_ve_organigrama_sin_editar(self):
        make_puesto(self.empresa_a, nombre="Oculto para empleado")
        self.client.force_login(self.empleado_a)
        response = self.client.get(reverse("organizacion:organigrama"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Nuevo puesto")
        self.assertContains(response, "No tenés un puesto asignado")

    def test_admin_no_edita_puesto_de_otra_empresa(self):
        puesto_b = make_puesto(self.empresa_b, nombre="Ajeno")
        self.client.force_login(self.admin_a)
        response = self.client.get(
            reverse("organizacion:puesto_editar", args=[puesto_b.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_crear_puesto(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("organizacion:puesto_crear"),
            {
                "nombre": "Líder",
                "descripcion": "Coordina el equipo",
                "area": "",
                "puesto_superior": "",
                "activo": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Puesto.objects.filter(nombre="Líder", empresa=self.empresa_a).exists()
        )
        self.assertContains(response, "Puesto guardado correctamente.")

    def test_login_requerido(self):
        response = self.client.get(reverse("organizacion:puestos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)


class CompetenciaRapidaTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.otra = make_empresa()
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.empleado = make_usuario(self.empresa, rol="empleado")

    def test_admin_crea_competencia_json(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("organizacion:competencia_rapida"),
            {
                "nombre": "Pensamiento crítico",
                "tipo": Competencia.Tipo.ACTITUDINAL,
                "descripcion": "Analiza problemas.",
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["nombre"], "Pensamiento crítico")
        competencia = Competencia.objects.get(pk=payload["id"])
        self.assertEqual(competencia.empresa_id, self.empresa.pk)
        self.assertTrue(competencia.activa)
        self.assertEqual(competencia.tipo, Competencia.Tipo.ACTITUDINAL)

    def test_nombre_vacio_devuelve_400(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("organizacion:competencia_rapida"),
            {"nombre": "", "tipo": Competencia.Tipo.TECNICA},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("nombre", response.json()["errors"])

    def test_empleado_no_crea(self):
        self.client.force_login(self.empleado)
        response = self.client.post(
            reverse("organizacion:competencia_rapida"),
            {"nombre": "No debería", "tipo": Competencia.Tipo.TECNICA},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Competencia.objects.filter(nombre="No debería").exists()
        )

    def test_no_crea_en_otra_empresa(self):
        admin_b = make_usuario(self.otra, rol="admin_rrhh")
        self.client.force_login(admin_b)
        response = self.client.post(
            reverse("organizacion:competencia_rapida"),
            {"nombre": "Solo B", "tipo": Competencia.Tipo.TECNICA},
        )
        self.assertEqual(response.status_code, 201)
        competencia = Competencia.objects.get(nombre="Solo B")
        self.assertEqual(competencia.empresa_id, self.otra.pk)
        self.assertFalse(
            Competencia.objects.filter(
                nombre="Solo B", empresa=self.empresa
            ).exists()
        )
