from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from organizacion.models import Area


class UsuariosPermisosTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.admin = make_usuario(self.empresa, rol="admin_rrhh", email="rrhh@empresa.test")

    def test_empleado_no_accede_a_usuarios(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        self.client.force_login(empleado)
        response = self.client.get(reverse("cuentas:usuarios"))
        self.assertEqual(response.status_code, 403)

    def test_supervisor_no_crea_usuarios(self):
        supervisor = make_usuario(self.empresa, rol="supervisor")
        self.client.force_login(supervisor)
        response = self.client.get(reverse("cuentas:usuario_crear"))
        self.assertEqual(response.status_code, 403)
        response_post = self.client.post(
            reverse("cuentas:usuario_crear"),
            {
                "first_name": "Nuevo",
                "last_name": "Empleado",
                "email": "nuevo@empresa.test",
                "rol": "empleado",
            },
        )
        self.assertEqual(response_post.status_code, 403)
        self.assertFalse(Usuario.objects.filter(email="nuevo@empresa.test").exists())

    def test_email_duplicado_misma_empresa(self):
        make_usuario(self.empresa, email="dup@empresa.test")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("cuentas:usuario_crear"),
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "dup@empresa.test",
                "rol": "empleado",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un usuario con este correo en la empresa.")
        self.assertEqual(
            Usuario.objects.filter(empresa=self.empresa, email="dup@empresa.test").count(),
            1,
        )

    def test_email_igual_otra_empresa_permitido(self):
        otra = make_empresa()
        make_usuario(self.empresa, email="mismo@empresa.test")
        admin_b = make_usuario(otra, rol="admin_rrhh", email="rrhh@otra.test")
        self.client.force_login(admin_b)
        response = self.client.post(
            reverse("cuentas:usuario_crear"),
            {
                "first_name": "Luis",
                "last_name": "Gómez",
                "email": "mismo@empresa.test",
                "rol": "empleado",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Usuario.objects.filter(empresa=otra, email="mismo@empresa.test").exists()
        )
        self.assertEqual(Usuario.objects.filter(email="mismo@empresa.test").count(), 2)

    def test_admin_lista_solo_su_empresa(self):
        otra = make_empresa()
        make_usuario(otra, email="ajeno@otra.test")
        propio = make_usuario(self.empresa, email="propio@empresa.test")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cuentas:usuarios"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, propio.email)
        self.assertNotContains(response, "ajeno@otra.test")

    def test_filtro_por_area(self):
        area = Area.objects.create(empresa=self.empresa, nombre="Comercial")
        con_area = make_usuario(self.empresa, email="area@empresa.test", area=area)
        sin_area = make_usuario(self.empresa, email="sinarea@empresa.test")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cuentas:usuarios"), {"area": area.pk})
        self.assertContains(response, con_area.email)
        self.assertNotContains(response, sin_area.email)
