from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_area, make_empresa, make_puesto, make_usuario
from cuentas.models import Usuario


class UsuariosApiTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.admin = make_usuario(self.empresa, rol="admin_rrhh", email="rrhh@empresa.test")
        self.lista = reverse("usuarios-list")

    def autenticar(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_empleado_no_accede_a_usuarios(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        self.autenticar(empleado)
        response = self.client.get(self.lista)
        self.assertEqual(response.status_code, 403)

    def test_supervisor_no_crea_usuarios(self):
        supervisor = make_usuario(self.empresa, rol="supervisor")
        self.autenticar(supervisor)
        response = self.client.post(
            self.lista,
            {
                "first_name": "Nuevo",
                "last_name": "Empleado",
                "email": "nuevo@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Usuario.objects.filter(email="nuevo@empresa.test").exists())

    def test_email_duplicado_misma_empresa(self):
        make_usuario(self.empresa, email="dup@empresa.test")
        self.autenticar(self.admin)
        response = self.client.post(
            self.lista,
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "dup@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ya existe un usuario con este correo en la empresa.", response.data["email"])
        self.assertEqual(
            Usuario.objects.filter(empresa=self.empresa, email="dup@empresa.test").count(),
            1,
        )

    def test_email_igual_otra_empresa_permitido(self):
        otra = make_empresa()
        make_usuario(self.empresa, email="mismo@empresa.test")
        admin_b = make_usuario(otra, rol="admin_rrhh", email="rrhh@otra.test")
        self.autenticar(admin_b)
        response = self.client.post(
            self.lista,
            {
                "first_name": "Luis",
                "last_name": "Gómez",
                "email": "mismo@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Usuario.objects.filter(empresa=otra, email="mismo@empresa.test").exists())
        self.assertEqual(Usuario.objects.filter(email="mismo@empresa.test").count(), 2)

    def test_admin_lista_solo_su_empresa(self):
        otra = make_empresa()
        make_usuario(otra, email="ajeno@otra.test")
        propio = make_usuario(self.empresa, email="propio@empresa.test")
        self.autenticar(self.admin)
        response = self.client.get(self.lista)
        self.assertEqual(response.status_code, 200)
        emails = [item["email"] for item in response.data["results"]]
        self.assertIn(propio.email, emails)
        self.assertNotIn("ajeno@otra.test", emails)

    def test_filtro_por_area(self):
        area = make_area(self.empresa, nombre="Comercial")
        con_area = make_usuario(self.empresa, email="area@empresa.test", area=area)
        sin_area = make_usuario(self.empresa, email="sinarea@empresa.test")
        self.autenticar(self.admin)
        response = self.client.get(self.lista, {"area": area.pk})
        emails = [item["email"] for item in response.data["results"]]
        self.assertIn(con_area.email, emails)
        self.assertNotIn(sin_area.email, emails)

    def test_alta_rechaza_area_o_puesto_inactivos_y_rol_fuera_de_gestion(self):
        area = make_area(self.empresa, nombre="Cerrada", activa=False)
        puesto = make_puesto(self.empresa, nombre="Archivado", activo=False)
        self.autenticar(self.admin)
        por_area = self.client.post(
            self.lista,
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana-area@empresa.test",
                "rol": "empleado",
                "area": area.pk,
            },
            format="json",
        )
        por_puesto = self.client.post(
            self.lista,
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana-puesto@empresa.test",
                "rol": "empleado",
                "puesto": puesto.pk,
            },
            format="json",
        )
        por_rol = self.client.post(
            self.lista,
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana-rol@empresa.test",
                "rol": "superadmin",
            },
            format="json",
        )
        self.assertEqual(por_area.status_code, 400)
        self.assertEqual(por_puesto.status_code, 400)
        self.assertEqual(por_rol.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email="ana-area@empresa.test").exists())
        self.assertFalse(Usuario.objects.filter(email="ana-puesto@empresa.test").exists())
        self.assertFalse(Usuario.objects.filter(email="ana-rol@empresa.test").exists())

    def test_clave_temporal_solo_en_el_alta(self):
        self.autenticar(self.admin)
        alta = self.client.post(
            self.lista,
            {
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "temporal@empresa.test",
                "rol": "empleado",
            },
            format="json",
        )
        self.assertEqual(alta.status_code, 201)
        self.assertTrue(alta.data["clave_temporal"])
        self.assertTrue(alta.data["must_change_password"])
        usuario = Usuario.objects.get(pk=alta.data["id"])
        self.assertTrue(usuario.check_password(alta.data["clave_temporal"]))
        clave_hash = usuario.password
        edicion = self.client.patch(
            reverse("usuarios-detail", args=[usuario.pk]),
            {"first_name": "Ana María"},
            format="json",
        )
        self.assertEqual(edicion.status_code, 200)
        self.assertNotIn("clave_temporal", edicion.data)
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, clave_hash)
        self.assertEqual(usuario.first_name, "Ana María")

    def test_edicion_permite_area_inactiva(self):
        area = make_area(self.empresa, activa=False)
        usuario = make_usuario(self.empresa, email="edit@empresa.test")
        self.autenticar(self.admin)
        response = self.client.patch(
            reverse("usuarios-detail", args=[usuario.pk]),
            {"area": area.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(usuario.area_id, area.pk)

    def test_desactivar_bloquear_y_reset(self):
        objetivo = make_usuario(self.empresa, email="objetivo@empresa.test")
        self.autenticar(self.admin)
        desactivar = self.client.post(reverse("usuarios-desactivar", args=[objetivo.pk]))
        self.assertEqual(desactivar.status_code, 200)
        objetivo.refresh_from_db()
        self.assertFalse(objetivo.is_active)

        objetivo.is_active = True
        objetivo.save(update_fields=["is_active"])
        bloquear = self.client.post(reverse("usuarios-bloquear", args=[objetivo.pk]))
        self.assertEqual(bloquear.status_code, 200)
        objetivo.refresh_from_db()
        self.assertTrue(objetivo.bloqueado)

        reset = self.client.post(reverse("usuarios-reset-clave", args=[objetivo.pk]))
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(reset.data["clave_temporal"])
        objetivo.refresh_from_db()
        self.assertTrue(objetivo.must_change_password)
        self.assertTrue(objetivo.check_password(reset.data["clave_temporal"]))

    def test_no_actua_sobre_si_mismo(self):
        self.autenticar(self.admin)
        response = self.client.post(reverse("usuarios-desactivar", args=[self.admin.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("propia cuenta", response.data["detail"])
