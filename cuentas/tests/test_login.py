from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from empresas.models import Empresa


class LoginTests(TestCase):
    def setUp(self):
        self.url = reverse("cuentas:login")
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
            {"username": self.usuario.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

    def test_login_fail(self):
        response = self.client.post(
            self.url,
            {"username": self.usuario.email, "password": "clave-incorrecta"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email o contraseña incorrectos.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_bloqueado(self):
        self.usuario.bloqueado = True
        self.usuario.save(update_fields=["bloqueado"])
        response = self.client.post(
            self.url,
            {"username": self.usuario.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tu cuenta está bloqueada.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_empresa_suspendida(self):
        self.empresa.estado = Empresa.Estado.SUSPENDIDA
        self.empresa.save(update_fields=["estado"])
        response = self.client.post(
            self.url,
            {"username": self.usuario.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La empresa está suspendida.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_muestra_olvide_mi_clave(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Olvidé mi clave")
        self.assertContains(response, reverse("cuentas:password_reset"))

    def test_superadmin_redirige_a_empresas(self):
        Usuario.objects.create_superuser(
            email="super@teampulse.test",
            password=self.password,
        )
        response = self.client.post(
            self.url,
            {"username": "super@teampulse.test", "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/empresas/"))

    def test_logout_post(self):
        self.client.force_login(self.usuario)
        response = self.client.post(reverse("cuentas:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_must_change_password_redirige(self):
        self.usuario.must_change_password = True
        self.usuario.save(update_fields=["must_change_password"])
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cuentas:password_change"))
