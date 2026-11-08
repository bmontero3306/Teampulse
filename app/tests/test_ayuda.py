from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.ayuda import paginas_visibles
from app.tests.factories import make_empresa, make_usuario


class AyudaApiTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_ayuda_requiere_token(self):
        response = self.client.get("/api/v1/ayuda/")
        self.assertEqual(response.status_code, 401)

    def test_empleado_ve_indice_y_flujo(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self._auth(usuario)
        indice = self.client.get("/api/v1/ayuda/")
        self.assertEqual(indice.status_code, 200)
        titulos = [p["titulo"] for p in indice.data["paginas"]]
        self.assertIn("Cómo funciona TeamPulse", titulos)
        self.assertIn("Flujo de una evaluación", titulos)
        self.assertNotIn("Reportes ISO 9001", titulos)
        self.assertNotIn("Auditoría", titulos)
        self.assertNotIn("Empresas y plataforma", titulos)
        grupos = {grupo["nombre"] for grupo in indice.data["grupos"]}
        self.assertIn("Empezar", grupos)
        self.assertIn("Evaluación", grupos)

        flujo = self.client.get("/api/v1/ayuda/flujo/")
        self.assertEqual(flujo.status_code, 200)
        self.assertEqual(flujo.data["titulo"], "Flujo de una evaluación")
        texto = " ".join(flujo.data["cuerpo"])
        self.assertIn("Pendiente de autoevaluación", texto)
        self.assertIn("supervisor no ve la autoevaluación", texto)

    def test_empleado_no_ve_paginas_de_rrhh(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self._auth(usuario)
        for slug in ("organizacion", "plantillas", "ciclos", "reportes", "auditoria", "empresas"):
            response = self.client.get(f"/api/v1/ayuda/{slug}/")
            self.assertEqual(response.status_code, 404, slug)

    def test_admin_ve_ciclos_y_reportes(self):
        usuario = make_usuario(self.empresa, rol="admin_rrhh")
        self._auth(usuario)
        ciclos = self.client.get("/api/v1/ayuda/ciclos/")
        self.assertEqual(ciclos.status_code, 200)
        texto_ciclos = " ".join(ciclos.data["cuerpo"])
        self.assertIn("borrador", texto_ciclos)
        self.assertIn("un ciclo activo por empresa", texto_ciclos)
        reportes = self.client.get("/api/v1/ayuda/reportes/")
        self.assertEqual(reportes.status_code, 200)
        self.assertEqual(reportes.data["titulo"], "Reportes")
        self.assertIn("PDF", " ".join(reportes.data["cuerpo"]))

    def test_superadmin_ve_empresas_sin_contexto(self):
        usuario = make_usuario(None, rol="superadmin")
        self._auth(usuario)
        response = self.client.get("/api/v1/ayuda/empresas/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Suspendida", " ".join(response.data["cuerpo"]))

    def test_slug_inexistente_da_404(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self._auth(usuario)
        response = self.client.get("/api/v1/ayuda/no-existe/")
        self.assertEqual(response.status_code, 404)

    def test_paginas_visibles_por_rol(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        slugs = [p["slug"] for p in paginas_visibles(empleado, self.empresa)]
        self.assertEqual(
            slugs,
            ["inicio", "roles", "flujo", "conformidad", "notificaciones"],
        )
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        slugs_admin = [p["slug"] for p in paginas_visibles(admin, self.empresa)]
        self.assertIn("ciclos", slugs_admin)
        self.assertIn("reportes", slugs_admin)
        self.assertNotIn("empresas", slugs_admin)
