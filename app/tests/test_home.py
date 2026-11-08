from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario


class HomeApiTests(APITestCase):
    def test_dashboard_y_ayuda_anonimos_responden_401(self):
        dashboard = self.client.get("/api/v1/dashboard/")
        ayuda = self.client.get("/api/v1/ayuda/")
        pagina = self.client.get("/api/v1/ayuda/inicio/")
        self.assertEqual(dashboard.status_code, 401)
        self.assertEqual(ayuda.status_code, 401)
        self.assertEqual(pagina.status_code, 401)

    def test_dashboard_autenticado_es_json(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ciclo_activo", response.data)
        self.assertIn("mostrar_pendientes", response.data)
        self.assertTrue(response.data["mostrar_pendientes"])
