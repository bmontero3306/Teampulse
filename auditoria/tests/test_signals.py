from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.test import RequestFactory, TestCase

from app.tests.factories import make_empresa, make_usuario
from auditoria.constants import Accion
from auditoria.models import AuditLog
from cuentas.models import Usuario


class SenalesAuthTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = make_empresa()
        self.usuario = make_usuario(self.empresa, rol=Usuario.Rol.ADMIN_RRHH)

    def _request(self):
        request = self.factory.post("/cuentas/login/")
        request.user = self.usuario
        request.empresa = self.empresa
        request.META["REMOTE_ADDR"] = "10.0.0.8"
        request.META["HTTP_USER_AGENT"] = "Agente-Test"
        return request

    def test_login_registra_auditoria(self):
        request = self._request()
        user_logged_in.send(
            sender=Usuario,
            request=request,
            user=self.usuario,
        )
        log = AuditLog.objects.get(accion=Accion.LOGIN)
        self.assertEqual(log.usuario, self.usuario)
        self.assertEqual(log.empresa, self.empresa)
        self.assertEqual(log.payload.get("email"), self.usuario.email)
        self.assertNotIn("password", log.payload)

    def test_logout_registra_auditoria(self):
        request = self._request()
        user_logged_out.send(
            sender=Usuario,
            request=request,
            user=self.usuario,
        )
        log = AuditLog.objects.get(accion=Accion.LOGOUT)
        self.assertEqual(log.usuario, self.usuario)

    def test_login_fallido_no_guarda_password(self):
        request = self.factory.post("/cuentas/login/")
        request.user = None
        request.empresa = None
        user_login_failed.send(
            sender=Usuario,
            credentials={"email": "alguien@test.com", "password": "no-debe-quedar"},
            request=request,
        )
        log = AuditLog.objects.get(accion=Accion.LOGIN_FALLIDO)
        self.assertEqual(log.payload.get("email"), "alguien@test.com")
        self.assertNotIn("password", log.payload)
        self.assertNotIn("no-debe-quedar", log.payload_pretty)
