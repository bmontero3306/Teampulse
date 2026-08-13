from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from app.mixins import RolRequiredMixin
from app.tests.factories import make_empresa, make_usuario


class VistaSoloAdmin(RolRequiredMixin, View):
    roles_permitidos = ["admin_rrhh"]

    def get(self, request):
        return HttpResponse("ok")


class RolRequiredMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = make_empresa()

    def test_mixin_rechaza_rol_incorrecto(self):
        empleado = make_usuario(self.empresa, rol="empleado")
        request = self.factory.get("/restringido/")
        request.user = empleado
        with self.assertRaises(PermissionDenied):
            VistaSoloAdmin.as_view()(request)

    def test_mixin_permite_rol_correcto(self):
        admin = make_usuario(self.empresa, rol="admin_rrhh")
        request = self.factory.get("/restringido/")
        request.user = admin
        response = VistaSoloAdmin.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
