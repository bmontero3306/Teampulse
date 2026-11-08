from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

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


class UsuarioUnicidadApiTests(APITestCase):
    def test_api_rechaza_email_duplicado_y_permite_otra_empresa(self):
        empresa = make_empresa()
        otra = make_empresa()
        make_usuario(empresa, email="mismo@empresa.test")
        admin = make_usuario(empresa, rol="admin_rrhh", email="rrhh@empresa.test")
        admin_b = make_usuario(otra, rol="admin_rrhh", email="rrhh@otra.test")
        token, _ = Token.objects.get_or_create(user=admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        duplicado = self.client.post(
            reverse("usuarios-list"),
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "mismo@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(duplicado.status_code, 400)
        self.assertEqual(
            Usuario.objects.filter(empresa=empresa, email="mismo@empresa.test").count(),
            1,
        )

        token_b, _ = Token.objects.get_or_create(user=admin_b)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_b.key}")
        permitido = self.client.post(
            reverse("usuarios-list"),
            {
                "first_name": "Luis",
                "last_name": "Gómez",
                "email": "mismo@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(permitido.status_code, 201)
        self.assertEqual(Usuario.objects.filter(email="mismo@empresa.test").count(), 2)
