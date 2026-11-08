from django.test import TestCase

from app.tests.factories import make_empresa, make_usuario


class EmpresaMiddlewareTests(TestCase):
    def test_middleware_asigna_empresa(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        self.client.force_login(usuario)
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.wsgi_request.empresa, empresa)

    def test_middleware_superadmin_usa_sesion(self):
        empresa = make_empresa()
        superadmin = make_usuario(None, rol="superadmin", is_staff=True, is_superuser=True)
        self.client.force_login(superadmin)
        session = self.client.session
        session["empresa_id"] = empresa.pk
        session.save()
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.wsgi_request.empresa, empresa)
