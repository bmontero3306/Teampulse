from django.core.exceptions import ValidationError
from django.test import TestCase

from app.tests.factories import (
    make_area,
    make_competencia,
    make_empresa,
    make_puesto,
    make_usuario,
)
from organizacion.models import Area, Competencia, Puesto, PuestoCompetencia


class TenantOrganizacionTests(TestCase):
    def setUp(self):
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.admin_a = make_usuario(self.empresa_a, rol="admin_rrhh")
        self.admin_b = make_usuario(self.empresa_b, rol="admin_rrhh")
        self.puesto_a = make_puesto(self.empresa_a, nombre="Puesto A")
        self.puesto_b = make_puesto(self.empresa_b, nombre="Puesto B")
        self.comp_a = make_competencia(self.empresa_a, nombre="Comp A")
        self.comp_b = make_competencia(self.empresa_b, nombre="Comp B")
        make_area(self.empresa_a, nombre="Área A")
        make_area(self.empresa_b, nombre="Área B")

    def test_competencia_otra_empresa_no_se_asigna(self):
        pc = PuestoCompetencia(
            puesto=self.puesto_a,
            competencia=self.comp_b,
            ponderacion=50,
        )
        with self.assertRaises(ValidationError):
            pc.full_clean()

    def test_competencia_misma_empresa_si_se_asigna(self):
        pc = PuestoCompetencia(
            puesto=self.puesto_a,
            competencia=self.comp_a,
            ponderacion=50,
        )
        pc.full_clean()
        pc.save()
        self.assertTrue(
            PuestoCompetencia.objects.filter(
                puesto=self.puesto_a, competencia=self.comp_a
            ).exists()
        )

    def test_querysets_filtran_por_empresa(self):
        self.assertEqual(
            list(
                Puesto.objects.for_empresa(self.empresa_a).values_list(
                    "nombre", flat=True
                )
            ),
            ["Puesto A"],
        )
        self.assertEqual(
            list(
                Area.objects.for_empresa(self.empresa_a).values_list(
                    "nombre", flat=True
                )
            ),
            ["Área A"],
        )
        self.assertEqual(
            list(
                Competencia.objects.for_empresa(self.empresa_a).values_list(
                    "nombre", flat=True
                )
            ),
            ["Comp A"],
        )

    def test_area_padre_de_otra_empresa_invalida(self):
        area_a = Area.objects.for_empresa(self.empresa_a).get()
        area_b = Area.objects.for_empresa(self.empresa_b).get()
        area_a.area_padre = area_b
        with self.assertRaises(ValidationError):
            area_a.full_clean()
