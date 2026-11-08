from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from empresas.models import Empresa


class ApiAuthTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.password = "clave-test-123"
        self.usuario = make_usuario(
            self.empresa,
            rol="admin_rrhh",
            email="admin@empresa.test",
            password=self.password,
        )
        self.login_url = reverse("api-login")

    def test_login_devuelve_token(self):
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["usuario"]["email"], self.usuario.email)
        self.assertTrue(Token.objects.filter(user=self.usuario).exists())

    def test_login_clave_incorrecta(self):
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": "no-es"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("incorrectos", response.data["detail"])

    def test_login_bloqueado(self):
        self.usuario.bloqueado = True
        self.usuario.save(update_fields=["bloqueado"])
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bloqueada", response.data["detail"])

    def test_login_empresa_suspendida(self):
        self.empresa.estado = Empresa.Estado.SUSPENDIDA
        self.empresa.save(update_fields=["estado"])
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("suspendida", response.data["detail"])

    def test_login_inactivo(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("desactivada", response.data["detail"])

    def test_login_empresa_inactiva(self):
        self.empresa.estado = Empresa.Estado.INACTIVA
        self.empresa.save(update_fields=["estado"])
        response = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("no está activa", response.data["detail"])

    def test_login_sin_empresa(self):
        Usuario.objects.create_user(
            email="suelto@empresa.test",
            password=self.password,
            rol=Usuario.Rol.EMPLEADO,
            empresa=None,
            is_active=True,
            must_change_password=False,
        )
        response = self.client.post(
            self.login_url,
            {"email": "suelto@empresa.test", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("no está asociada a una empresa", response.data["detail"])

    def test_me_y_logout(self):
        token = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me = self.client.get(reverse("api-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["empresa_actual"]["id"], self.empresa.pk)
        self.assertTrue(any(item["clave"] == "usuarios" for item in me.data["nav"]))
        logout = self.client.post(reverse("api-logout"))
        self.assertEqual(logout.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.usuario).exists())

    def test_must_change_password_bloquea_dashboard(self):
        self.usuario.must_change_password = True
        self.usuario.save(update_fields=["must_change_password"])
        token = self.client.post(
            self.login_url,
            {"email": self.usuario.email, "password": self.password},
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        bloqueado = self.client.get(reverse("api-dashboard"))
        self.assertEqual(bloqueado.status_code, 403)
        self.assertEqual(bloqueado.json()["detail"]["code"], "must_change_password")
        cambio = self.client.post(
            reverse("api-password-change"),
            {"old_password": self.password, "new_password": "ClaveNueva-2026"},
            format="json",
        )
        self.assertEqual(cambio.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.must_change_password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {cambio.data['token']}")
        ok = self.client.get(reverse("api-dashboard"))
        self.assertEqual(ok.status_code, 200)

    def test_superadmin_usa_header_de_empresa(self):
        superadmin = Usuario.objects.create_superuser(
            email="super@teampulse.test",
            password=self.password,
        )
        token = self.client.post(
            self.login_url,
            {"email": superadmin.email, "password": self.password},
            format="json",
        ).data["token"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token}",
            HTTP_X_EMPRESA_ID=str(self.empresa.pk),
        )
        me = self.client.get(reverse("api-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["empresa_actual"]["id"], self.empresa.pk)
        self.assertTrue(any(item["clave"] == "usuarios" for item in me.data["nav"]))
