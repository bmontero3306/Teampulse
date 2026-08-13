from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario


class EmpresaMiddlewareTests(TestCase):
    def test_middleware_asigna_empresa(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        self.client.force_login(usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.empresa, empresa)

    def test_middleware_superadmin_usa_sesion(self):
        empresa = make_empresa()
        superadmin = make_usuario(None, rol="superadmin", is_staff=True, is_superuser=True)
        self.client.force_login(superadmin)
        session = self.client.session
        session["empresa_id"] = empresa.pk
        session.save()
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.wsgi_request.empresa, empresa)
