from django.test import TestCase

from app.querysets import for_empresa
from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario


class ForEmpresaTests(TestCase):
    def test_filtra_por_empresa(self):
        empresa_a = make_empresa()
        empresa_b = make_empresa()
        make_usuario(empresa_a, email="a@empresa.test")
        make_usuario(empresa_b, email="b@empresa.test")

        qs = for_empresa(Usuario.objects.all(), empresa_a)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.get().email, "a@empresa.test")

    def test_sin_empresa_devuelve_vacio(self):
        empresa = make_empresa()
        make_usuario(empresa)
        self.assertEqual(for_empresa(Usuario.objects.all(), None).count(), 0)
