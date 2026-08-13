from django.core.exceptions import ValidationError
from django.test import TestCase

from app.tests.factories import make_area, make_empresa, make_puesto
from organizacion.models import Area, Puesto
from organizacion.services import (
    JerarquiaCircularError,
    puestos_hijos,
    query_organigrama,
    validar_jerarquia_areas,
    validar_jerarquia_puestos,
)


class JerarquiaPuestosTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.gerente = make_puesto(self.empresa, nombre="Gerente")
        self.jefe = make_puesto(
            self.empresa, nombre="Jefe", puesto_superior=self.gerente
        )
        self.analista = make_puesto(
            self.empresa, nombre="Analista", puesto_superior=self.jefe
        )

    def test_referencia_circular_directa_rechazada(self):
        with self.assertRaises(JerarquiaCircularError):
            validar_jerarquia_puestos(self.gerente, self.jefe)

    def test_referencia_circular_en_cadena_rechazada(self):
        with self.assertRaises(JerarquiaCircularError):
            validar_jerarquia_puestos(self.gerente, self.analista)

    def test_puesto_no_puede_ser_su_propio_superior(self):
        with self.assertRaises(JerarquiaCircularError):
            validar_jerarquia_puestos(self.gerente, self.gerente)

    def test_asignar_superior_valido(self):
        otro = make_puesto(self.empresa, nombre="Director")
        self.assertTrue(validar_jerarquia_puestos(self.gerente, otro))

    def test_full_clean_rechaza_ciclo(self):
        self.gerente.puesto_superior = self.analista
        with self.assertRaises(ValidationError):
            self.gerente.full_clean()

    def test_puestos_hijos(self):
        hijos = list(puestos_hijos(self.gerente))
        self.assertEqual(hijos, [self.jefe])
        self.assertEqual(list(puestos_hijos(self.jefe)), [self.analista])

    def test_query_organigrama_raices_e_hijos(self):
        raices = query_organigrama(self.empresa)
        self.assertEqual(len(raices), 1)
        self.assertEqual(raices[0].pk, self.gerente.pk)
        self.assertEqual(
            [h.pk for h in raices[0].hijos_organigrama], [self.jefe.pk]
        )
        self.assertEqual(
            [h.pk for h in raices[0].hijos_organigrama[0].hijos_organigrama],
            [self.analista.pk],
        )

    def test_soft_delete_no_borra_puesto(self):
        pk = self.analista.pk
        self.analista.delete()
        self.analista.refresh_from_db()
        self.assertFalse(self.analista.activo)
        self.assertTrue(Puesto.objects.filter(pk=pk).exists())


class JerarquiaAreasTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.direccion = make_area(self.empresa, nombre="Dirección")
        self.operaciones = make_area(
            self.empresa, nombre="Operaciones", area_padre=self.direccion
        )
        self.calidad = make_area(
            self.empresa, nombre="Calidad", area_padre=self.operaciones
        )

    def test_referencia_circular_area_rechazada(self):
        with self.assertRaises(JerarquiaCircularError):
            validar_jerarquia_areas(self.direccion, self.calidad)

    def test_full_clean_rechaza_ciclo_area(self):
        self.direccion.area_padre = self.operaciones
        with self.assertRaises(ValidationError):
            self.direccion.full_clean()

    def test_soft_delete_no_borra_area(self):
        pk = self.calidad.pk
        self.calidad.delete()
        self.calidad.refresh_from_db()
        self.assertFalse(self.calidad.activa)
        self.assertTrue(Area.objects.filter(pk=pk).exists())
