from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from empresas.models import Empresa


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LoginApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("api-login")
        self.empresa = make_empresa()
        self.password = "clave-test-123"
        self.usuario = make_usuario(
            self.empresa,
            rol="admin_rrhh",
            email="admin@empresa.test",
            password=self.password,
        )

    def test_login_ok(self):
        response = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertTrue(Token.objects.filter(user=self.usuario).exists())
        self.assertTrue(any(item["href"] == "/dashboard" for item in response.data["nav"]))

    def test_login_fail(self):
        response = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": "clave-incorrecta"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("incorrectos", response.data["detail"])
        self.assertFalse(Token.objects.filter(user=self.usuario).exists())

    def test_login_bloqueado(self):
        self.usuario.bloqueado = True
        self.usuario.save(update_fields=["bloqueado"])
        response = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bloqueada", response.data["detail"])
        self.assertFalse(Token.objects.filter(user=self.usuario).exists())

    def test_login_empresa_suspendida(self):
        self.empresa.estado = Empresa.Estado.SUSPENDIDA
        self.empresa.save(update_fields=["estado"])
        response = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("suspendida", response.data["detail"])
        self.assertFalse(Token.objects.filter(user=self.usuario).exists())

    def test_recuperar_envia_enlace_de_la_spa(self):
        response = self.client.post(
            reverse("api-password-reset"),
            {"email": self.usuario.email},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"{settings.FRONTEND_ORIGIN}/recuperar/", mail.outbox[0].body)

    def test_recuperar_omite_cuenta_no_habilitada(self):
        self.usuario.bloqueado = True
        self.usuario.save(update_fields=["bloqueado"])
        response = self.client.post(
            reverse("api-password-reset"),
            {"email": self.usuario.email},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_superadmin_incluye_empresas(self):
        Usuario.objects.create_superuser(
            email="super@teampulse.test",
            password=self.password,
        )
        response = self.client.post(
            self.url,
            {"email": "super@teampulse.test", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["usuario"]["rol"], Usuario.Rol.SUPERADMIN)
        self.assertTrue(any(item["clave"] == "empresas" for item in response.data["nav"]))

    def test_logout(self):
        token = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.post(reverse("api-logout"))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.usuario).exists())

    def test_must_change_password_bloquea_api(self):
        self.usuario.must_change_password = True
        self.usuario.save(update_fields=["must_change_password"])
        token = self.client.post(
            self.url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.get(reverse("api-dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "must_change_password")
