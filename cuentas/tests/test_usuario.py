from django.db import IntegrityError
from django.test import TestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario


class UsuarioModelTests(TestCase):
    def test_identificador_es_email(self):
        self.assertEqual(Usuario.USERNAME_FIELD, "email")
        self.assertNotIn("username", [field.name for field in Usuario._meta.fields])

    def test_unique_email_por_empresa(self):
        empresa = make_empresa()
        make_usuario(empresa, email="mismo@empresa.test")
        with self.assertRaises(IntegrityError):
            make_usuario(empresa, email="mismo@empresa.test")

    def test_email_igual_en_otra_empresa_permitido(self):
        empresa_a = make_empresa()
        empresa_b = make_empresa()
        make_usuario(empresa_a, email="mismo@empresa.test")
        usuario_b = make_usuario(empresa_b, email="mismo@empresa.test")
        self.assertEqual(usuario_b.email, "mismo@empresa.test")
        self.assertEqual(
            Usuario.objects.filter(email="mismo@empresa.test").count(),
            2,
        )
