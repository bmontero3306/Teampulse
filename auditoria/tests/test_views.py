from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario
from auditoria.constants import Accion
from auditoria.models import AuditLog
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario


class AuditLogApiTests(APITestCase):
    def setUp(self):
        self.url = "/api/v1/auditoria/"
        self.empresa_a = make_empresa()
        self.empresa_b = make_empresa()
        self.admin = make_usuario(self.empresa_a, rol=Usuario.Rol.ADMIN_RRHH)
        self.otro = make_usuario(self.empresa_a, rol=Usuario.Rol.ADMIN_RRHH)
        self.empleado = make_usuario(self.empresa_a, rol=Usuario.Rol.EMPLEADO)
        self.supervisor = make_usuario(self.empresa_a, rol=Usuario.Rol.SUPERVISOR)
        self.ajeno = make_usuario(self.empresa_b, rol=Usuario.Rol.ADMIN_RRHH)
        self.superadmin = make_usuario(
            None,
            rol=Usuario.Rol.SUPERADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def _auth(self, usuario, empresa_id=None):
        token, _ = Token.objects.get_or_create(user=usuario)
        credenciales = {"HTTP_AUTHORIZATION": f"Token {token.key}"}
        if empresa_id is not None:
            credenciales["HTTP_X_EMPRESA_ID"] = str(empresa_id)
        self.client.credentials(**credenciales)

    def _crear_log(self, empresa, usuario, accion=Accion.CREAR, instance=None):
        return registrar_auditoria(
            request=None,
            accion=accion,
            instance=instance or empresa,
            payload={"origen": "test"},
            usuario=usuario,
            empresa=empresa,
        )

    def _fijar_fecha(self, log, dia):
        momento = timezone.make_aware(datetime.combine(dia, time(12, 0)))
        AuditLog.objects.filter(pk=log.pk).update(created_at=momento)

    def _ids(self, response):
        return {item["id"] for item in response.data["pagina"]["results"]}

    def test_anonimo_recibe_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_empleado_recibe_403(self):
        self._auth(self.empleado)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_supervisor_recibe_403(self):
        self._auth(self.supervisor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_admin_rrhh_ve_logs_de_su_empresa(self):
        log_a = self._crear_log(self.empresa_a, self.admin)
        log_b = self._crear_log(self.empresa_b, self.ajeno, accion="solo_b", instance=self.ajeno)
        self._auth(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(log_a.pk, ids)
        self.assertNotIn(log_b.pk, ids)
        fila = next(item for item in response.data["pagina"]["results"] if item["id"] == log_a.pk)
        self.assertEqual(fila["usuario_email"], self.admin.email)
        self.assertEqual(fila["empresa"], self.empresa_a.pk)
        self.assertEqual(fila["accion"], Accion.CREAR)
        self.assertEqual(fila["accion_display"], "Alta")
        self.assertEqual(fila["modelo"], "empresas.empresa")
        self.assertEqual(fila["object_id"], str(self.empresa_a.pk))
        self.assertEqual(fila["payload"], {"origen": "test"})
        self.assertTrue(fila["created_at"])
        self.assertIn(Accion.CREAR, response.data["acciones"])
        self.assertNotIn("solo_b", response.data["acciones"])
        self.assertIn("empresas.empresa", response.data["modelos"])
        self.assertNotIn("cuentas.usuario", response.data["modelos"])
        emails = {item["email"] for item in response.data["usuarios"]}
        self.assertIn(self.admin.email, emails)
        self.assertNotIn(self.ajeno.email, emails)

    def test_superadmin_sin_empresa_recibe_403(self):
        self._auth(self.superadmin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_superadmin_filtra_por_header_de_empresa(self):
        log_a = self._crear_log(self.empresa_a, self.admin)
        log_b = self._crear_log(self.empresa_b, self.ajeno)
        self._auth(self.superadmin, empresa_id=self.empresa_a.pk)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(log_a.pk, ids)
        self.assertNotIn(log_b.pk, ids)

    def test_filtro_por_accion_usuario_y_modelo(self):
        self._crear_log(self.empresa_a, self.admin, accion=Accion.CREAR)
        self._crear_log(self.empresa_a, self.otro, accion=Accion.EDITAR, instance=self.otro)
        self._auth(self.admin)

        por_accion = self.client.get(self.url, {"accion": Accion.EDITAR})
        self.assertEqual(por_accion.status_code, 200)
        self.assertEqual(
            {item["accion"] for item in por_accion.data["pagina"]["results"]},
            {Accion.EDITAR},
        )

        por_usuario = self.client.get(self.url, {"usuario": self.otro.pk})
        self.assertEqual(por_usuario.status_code, 200)
        self.assertEqual(
            {item["usuario"] for item in por_usuario.data["pagina"]["results"]},
            {self.otro.pk},
        )

        por_modelo = self.client.get(self.url, {"modelo": "cuentas.usuario"})
        self.assertEqual(por_modelo.status_code, 200)
        self.assertEqual(
            {item["modelo"] for item in por_modelo.data["pagina"]["results"]},
            {"cuentas.usuario"},
        )

    def test_filtro_por_fechas(self):
        hoy = timezone.localdate()
        ayer = hoy - timedelta(days=1)
        log_hoy = self._crear_log(self.empresa_a, self.admin, accion=Accion.CREAR)
        log_ayer = self._crear_log(self.empresa_a, self.admin, accion=Accion.EDITAR)
        self._fijar_fecha(log_hoy, hoy)
        self._fijar_fecha(log_ayer, ayer)
        self._auth(self.admin)

        response = self.client.get(
            self.url,
            {"fecha_desde": hoy.isoformat(), "fecha_hasta": hoy.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._ids(response), {log_hoy.pk})

        hasta_ayer = self.client.get(self.url, {"fecha_hasta": ayer.isoformat()})
        self.assertEqual(hasta_ayer.status_code, 200)
        self.assertEqual(self._ids(hasta_ayer), {log_ayer.pk})

    def test_fecha_invalida_recibe_400(self):
        self._auth(self.admin)
        response = self.client.get(self.url, {"fecha_desde": "no-es-fecha"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_desde", response.data)

    def test_usuario_ajeno_recibe_400(self):
        self._auth(self.admin)
        response = self.client.get(self.url, {"usuario": self.ajeno.pk})
        self.assertEqual(response.status_code, 400)
        self.assertIn("usuario", response.data)

    def test_detalle_de_otra_empresa_recibe_404(self):
        log_b = self._crear_log(self.empresa_b, self.ajeno)
        log_a = self._crear_log(self.empresa_a, self.admin)
        self._auth(self.admin)
        propio = self.client.get(f"{self.url}{log_a.pk}/")
        self.assertEqual(propio.status_code, 200)
        self.assertEqual(propio.data["id"], log_a.pk)
        ajeno = self.client.get(f"{self.url}{log_b.pk}/")
        self.assertEqual(ajeno.status_code, 404)
