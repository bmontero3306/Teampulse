from django.test import RequestFactory, TestCase

from app.tests.factories import make_empresa, make_usuario
from auditoria.constants import Accion
from auditoria.models import AuditLog
from auditoria.services import registrar_auditoria, sanitizar_payload
from cuentas.models import Usuario


def _request(usuario, empresa=None, ip="127.0.0.1", user_agent="Mozilla/Test"):
    factory = RequestFactory()
    request = factory.post("/auditoria/")
    request.user = usuario
    request.empresa = empresa if empresa is not None else getattr(usuario, "empresa", None)
    request.META["REMOTE_ADDR"] = ip
    request.META["HTTP_USER_AGENT"] = user_agent
    return request


class RegistrarAuditoriaTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.admin = make_usuario(self.empresa, rol=Usuario.Rol.ADMIN_RRHH)

    def test_save_de_empresa_via_servicio_genera_log(self):
        """WP1 audita desde vistas/servicios; el test llama registrar_auditoria directo."""
        request = _request(self.admin, self.empresa)
        log = registrar_auditoria(request, Accion.CREAR, self.empresa)

        self.assertIsInstance(log, AuditLog)
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.empresa, self.empresa)
        self.assertEqual(log.usuario, self.admin)
        self.assertEqual(log.accion, Accion.CREAR)
        self.assertEqual(log.modelo, "empresas.empresa")
        self.assertEqual(log.object_id, str(self.empresa.pk))
        self.assertEqual(log.ip, "127.0.0.1")
        self.assertIn("nombre", log.payload)
        self.assertEqual(log.payload["nombre"], self.empresa.nombre)

    def test_payload_no_contiene_password(self):
        request = _request(self.admin, self.empresa)
        registrar_auditoria(
            request,
            Accion.EDITAR,
            self.admin,
            payload={
                "email": self.admin.email,
                "password": "secreto-no-guardar",
                "token": "abc123",
                "perfil": {"password": "otra", "nombre": "Ana"},
            },
        )
        log = AuditLog.objects.get()
        serializado = log.payload_pretty.lower()
        self.assertNotIn("password", log.payload)
        self.assertNotIn("token", log.payload)
        self.assertNotIn("password", log.payload.get("perfil", {}))
        self.assertNotIn("secreto-no-guardar", serializado)
        self.assertNotIn("abc123", serializado)
        self.assertEqual(log.payload["email"], self.admin.email)
        self.assertEqual(log.payload["perfil"]["nombre"], "Ana")

    def test_snapshot_de_usuario_omite_password(self):
        request = _request(self.admin, self.empresa)
        log = registrar_auditoria(request, Accion.EDITAR, self.admin)
        self.assertNotIn("password", log.payload)
        self.assertNotIn("password", log.payload_pretty.lower())

    def test_kwargs_extra_no_rompen_la_firma(self):
        log = registrar_auditoria(
            request=None,
            accion=Accion.EXPORTAR,
            instance=self.empresa,
            payload={"formato": "pdf"},
            usuario=self.admin,
            empresa=self.empresa,
            extra_ignorado=True,
        )
        self.assertEqual(log.accion, Accion.EXPORTAR)
        self.assertEqual(log.payload["formato"], "pdf")
        self.assertEqual(log.usuario, self.admin)

    def test_evento_sin_empresa_permite_empresa_nula(self):
        log = registrar_auditoria(
            None,
            Accion.LOGIN_FALLIDO,
            None,
            payload={"email": "nadie@test.com"},
        )
        self.assertIsNone(log.empresa)
        self.assertIsNone(log.usuario)
        self.assertEqual(log.accion, Accion.LOGIN_FALLIDO)


class SanitizarPayloadTests(TestCase):
    def test_elimina_claves_sensibles_anidadas(self):
        limpio = sanitizar_payload(
            {
                "password": "x",
                "access_token": "y",
                "ok": 1,
                "hijo": {"refresh_token": "z", "id": 9},
            }
        )
        self.assertEqual(limpio, {"ok": 1, "hijo": {"id": 9}})
