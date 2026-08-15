from django.test import TestCase
from django.urls import reverse

from app.ayuda import paginas_visibles
from app.tests.factories import make_empresa, make_usuario


class AyudaViewsTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()

    def test_ayuda_requiere_login(self):
        response = self.client.get(reverse("app:ayuda"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_empleado_ve_indice_y_flujo(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self.client.force_login(usuario)
        indice = self.client.get(reverse("app:ayuda"))
        self.assertEqual(indice.status_code, 200)
        self.assertContains(indice, "Cómo funciona TeamPulse")
        self.assertContains(indice, "Flujo de una evaluación")
        self.assertNotContains(indice, "Reportes ISO 9001")
        self.assertNotContains(indice, "Auditoría")
        self.assertNotContains(indice, "Empresas y plataforma")

        flujo = self.client.get(reverse("app:ayuda_pagina", args=["flujo"]))
        self.assertEqual(flujo.status_code, 200)
        self.assertContains(flujo, "Pendiente de autoevaluación")
        self.assertContains(flujo, "Pendiente de conformidad")
        self.assertContains(flujo, "Cerrada con observación")

    def test_empleado_no_ve_paginas_de_rrhh(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self.client.force_login(usuario)
        for slug in ("organizacion", "plantillas", "ciclos", "reportes", "auditoria", "empresas"):
            response = self.client.get(reverse("app:ayuda_pagina", args=[slug]))
            self.assertEqual(response.status_code, 403, slug)

    def test_admin_ve_ciclos_y_reportes(self):
        usuario = make_usuario(self.empresa, rol="admin_rrhh")
        self.client.force_login(usuario)
        ciclos = self.client.get(reverse("app:ayuda_pagina", args=["ciclos"]))
        self.assertEqual(ciclos.status_code, 200)
        self.assertContains(ciclos, "Borrador")
        self.assertContains(ciclos, "un ciclo activo por empresa")
        reportes = self.client.get(reverse("app:ayuda_pagina", args=["reportes"]))
        self.assertEqual(reportes.status_code, 200)
        self.assertContains(reportes, "ISO 9001")

    def test_superadmin_ve_empresas_sin_contexto(self):
        usuario = make_usuario(None, rol="superadmin")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:ayuda_pagina", args=["empresas"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suspendida")
        self.assertContains(response, "multi-tenant")

    def test_slug_inexistente_da_404(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:ayuda_pagina", args=["no-existe"]))
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
