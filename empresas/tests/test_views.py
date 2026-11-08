from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario
from empresas.models import Empresa


def _datos(**kwargs):
    data = {
        "nombre": "Nueva Co",
        "razon_social": "Nueva Co S.A.",
        "cuit": "30999999999",
        "email_contacto": "nueva@test.com",
        "telefono": "1111",
        "direccion": "Calle 123",
        "estado": Empresa.Estado.ACTIVA,
    }
    data.update(kwargs)
    return data


class ApiEmpresasTestCase(APITestCase):
    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class PermisosEmpresasTests(ApiEmpresasTestCase):
    def setUp(self):
        super().setUp()
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.superadmin = make_usuario(
            None, rol="superadmin", is_staff=True, is_superuser=True
        )
        self.admin_a = make_usuario(self.empresa_a, rol="admin_rrhh")
        self.empleado_a = make_usuario(self.empresa_a, rol="empleado")

    def test_anonimo_no_lista(self):
        response = self.client.get("/api/v1/empresas/")
        self.assertEqual(response.status_code, 401)

    def test_superadmin_ve_lista(self):
        self._auth(self.superadmin)
        response = self.client.get("/api/v1/empresas/")
        self.assertEqual(response.status_code, 200)
        nombres = [item["nombre"] for item in response.data["results"]]
        self.assertIn(self.empresa_a.nombre, nombres)
        self.assertIn(self.empresa_b.nombre, nombres)

    def test_empleado_no_accede_a_lista(self):
        self._auth(self.empleado_a)
        response = self.client.get("/api/v1/empresas/")
        self.assertEqual(response.status_code, 403)

    def test_admin_rrhh_no_accede_a_lista_plataforma(self):
        self._auth(self.admin_a)
        response = self.client.get("/api/v1/empresas/")
        self.assertEqual(response.status_code, 403)

    def test_admin_empresa_a_no_ve_empresa_b(self):
        self._auth(self.admin_a)
        propia = self.client.get(f"/api/v1/empresas/{self.empresa_a.pk}/")
        self.assertEqual(propia.status_code, 200)
        self.assertEqual(propia.data["nombre"], self.empresa_a.nombre)

        ajena = self.client.get(f"/api/v1/empresas/{self.empresa_b.pk}/")
        self.assertEqual(ajena.status_code, 404)

        editar = self.client.patch(
            f"/api/v1/empresas/{self.empresa_b.pk}/",
            {"nombre": "No deberia"},
            format="json",
        )
        self.assertEqual(editar.status_code, 404)

    def test_admin_rrhh_no_puede_crear_ni_suspender(self):
        self._auth(self.admin_a)
        crear = self.client.post("/api/v1/empresas/", _datos(), format="json")
        self.assertEqual(crear.status_code, 403)

        suspender = self.client.post(f"/api/v1/empresas/{self.empresa_a.pk}/suspender/")
        self.assertEqual(suspender.status_code, 403)

        activar = self.client.post(f"/api/v1/empresas/{self.empresa_a.pk}/activar/")
        self.assertEqual(activar.status_code, 403)

    def test_admin_rrhh_edita_ficha_propia_sin_desactivar(self):
        self._auth(self.admin_a)
        cuit_original = self.empresa_a.cuit
        razon_original = self.empresa_a.razon_social
        response = self.client.patch(
            f"/api/v1/empresas/{self.empresa_a.pk}/",
            {
                "nombre": "Empresa A Renombrada",
                "email_contacto": "nuevo@a.test",
                "telefono": "222",
                "direccion": "Nueva dir",
                "estado": Empresa.Estado.SUSPENDIDA,
                "cuit": "20111111111",
                "razon_social": "Otra razon",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.empresa_a.refresh_from_db()
        self.assertEqual(self.empresa_a.nombre, "Empresa A Renombrada")
        self.assertEqual(self.empresa_a.email_contacto, "nuevo@a.test")
        self.assertEqual(self.empresa_a.telefono, "222")
        self.assertEqual(self.empresa_a.direccion, "Nueva dir")
        self.assertEqual(self.empresa_a.estado, Empresa.Estado.ACTIVA)
        self.assertEqual(self.empresa_a.cuit, cuit_original)
        self.assertEqual(self.empresa_a.razon_social, razon_original)


class CrudEmpresasTests(ApiEmpresasTestCase):
    def setUp(self):
        super().setUp()
        self.superadmin = make_usuario(
            None, rol="superadmin", is_staff=True, is_superuser=True
        )
        self._auth(self.superadmin)

    def test_crear_empresa(self):
        response = self.client.post("/api/v1/empresas/", _datos(), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        empresa = Empresa.objects.get(cuit="30999999999")
        self.assertEqual(empresa.nombre, "Nueva Co")
        self.assertEqual(empresa.estado, Empresa.Estado.ACTIVA)

    def test_editar_y_pasar_a_inactiva(self):
        empresa = make_empresa()
        response = self.client.patch(
            f"/api/v1/empresas/{empresa.pk}/",
            _datos(
                nombre="Editada",
                razon_social=empresa.razon_social,
                cuit=empresa.cuit,
                email_contacto=empresa.email_contacto,
                estado=Empresa.Estado.INACTIVA,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nombre, "Editada")
        self.assertEqual(empresa.estado, Empresa.Estado.INACTIVA)

    def test_suspender_post(self):
        empresa = make_empresa()
        response = self.client.post(f"/api/v1/empresas/{empresa.pk}/suspender/")
        self.assertEqual(response.status_code, 200, response.content)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.SUSPENDIDA)
        self.assertFalse(empresa.permite_login)
        self.assertEqual(response.data["estado"], Empresa.Estado.SUSPENDIDA)

    def test_activar_post(self):
        empresa = make_empresa(estado=Empresa.Estado.SUSPENDIDA)
        response = self.client.post(f"/api/v1/empresas/{empresa.pk}/activar/")
        self.assertEqual(response.status_code, 200, response.content)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.ACTIVA)
        self.assertEqual(response.data["estado"], Empresa.Estado.ACTIVA)

    def test_filtro_por_estado(self):
        make_empresa(nombre="Activa X", estado=Empresa.Estado.ACTIVA)
        suspendida = make_empresa(nombre="Suspendida Y", estado=Empresa.Estado.SUSPENDIDA)
        response = self.client.get("/api/v1/empresas/", {"estado": "suspendida"})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [suspendida.pk])
        self.assertIn(suspendida.nombre, [item["nombre"] for item in response.data["results"]])


class SelectorEmpresaTests(ApiEmpresasTestCase):
    def test_superadmin_selecciona_empresa_por_header(self):
        empresa = make_empresa()
        superadmin = make_usuario(None, rol="superadmin", is_staff=True, is_superuser=True)
        self._auth(superadmin)
        response = self.client.get("/api/v1/empresas/", HTTP_X_EMPRESA_ID=str(empresa.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.empresa, empresa)

    def test_admin_rrhh_no_cambia_contexto_con_header(self):
        empresa = make_empresa()
        otra = make_empresa()
        admin = make_usuario(empresa, rol="admin_rrhh")
        self._auth(admin)
        response = self.client.get(
            f"/api/v1/empresas/{empresa.pk}/",
            HTTP_X_EMPRESA_ID=str(otra.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.empresa, empresa)
