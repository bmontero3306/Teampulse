from django.test import TestCase
from django.urls import reverse

from app.tests.factories import (
    make_area,
    make_competencia,
    make_empresa,
    make_puesto,
    make_usuario,
)
from organizacion.models import Puesto, PuestoCompetencia


def _formset_vacio(**extra):
    data = {
        "competencias-TOTAL_FORMS": "1",
        "competencias-INITIAL_FORMS": "0",
        "competencias-MIN_NUM_FORMS": "0",
        "competencias-MAX_NUM_FORMS": "1000",
        "competencias-0-competencia": "",
        "competencias-0-ponderacion": "",
    }
    data.update(extra)
    return data


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
                **_formset_vacio(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "circular")
        gerente.refresh_from_db()
        self.assertIsNone(gerente.puesto_superior_id)

    def test_competencia_otra_empresa_no_se_asigna_por_vista(self):
        puesto = make_puesto(self.empresa_a, nombre="Analista")
        make_competencia(self.empresa_a, nombre="Local")
        comp_b = make_competencia(self.empresa_b, nombre="Ajena")
        self.client.force_login(self.admin_a)
        self.client.post(
            reverse("organizacion:puesto_editar", args=[puesto.pk]),
            {
                "nombre": "Analista",
                "descripcion": "",
                "area": "",
                "puesto_superior": "",
                "activo": "on",
                **_formset_vacio(
                    **{
                        "competencias-0-competencia": str(comp_b.pk),
                        "competencias-0-ponderacion": "40",
                    }
                ),
            },
        )
        self.assertFalse(
            PuestoCompetencia.objects.filter(
                puesto=puesto, competencia=comp_b
            ).exists()
        )

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

    def test_crear_puesto_con_ponderacion_distinta_de_100(self):
        competencia = make_competencia(self.empresa_a, nombre="Comunicación")
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("organizacion:puesto_crear"),
            {
                "nombre": "Líder",
                "descripcion": "Coordina el equipo",
                "area": "",
                "puesto_superior": "",
                "activo": "on",
                **_formset_vacio(
                    **{
                        "competencias-0-competencia": str(competencia.pk),
                        "competencias-0-ponderacion": "40",
                    }
                ),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        puesto = Puesto.objects.get(nombre="Líder", empresa=self.empresa_a)
        self.assertTrue(
            PuestoCompetencia.objects.filter(
                puesto=puesto, competencia=competencia
            ).exists()
        )
        self.assertContains(response, "40%")
        self.assertContains(response, "Se recomienda 100%")

    def test_login_requerido(self):
        response = self.client.get(reverse("organizacion:puestos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)
