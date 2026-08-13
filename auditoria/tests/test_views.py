from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario
from auditoria.constants import Accion
from auditoria.models import AuditLog
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario


class AuditLogListaViewTests(TestCase):
    def setUp(self):
        self.url = reverse("auditoria:lista")
        self.empresa_a = make_empresa()
        self.empresa_b = make_empresa()
        self.admin = make_usuario(self.empresa_a, rol=Usuario.Rol.ADMIN_RRHH)
        self.empleado = make_usuario(self.empresa_a, rol=Usuario.Rol.EMPLEADO)
        self.supervisor = make_usuario(self.empresa_a, rol=Usuario.Rol.SUPERVISOR)
        self.superadmin = make_usuario(
            None,
            rol=Usuario.Rol.SUPERADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def _crear_log(self, empresa, usuario, accion=Accion.CREAR, instance=None):
        return registrar_auditoria(
            request=None,
            accion=accion,
            instance=instance or empresa,
            payload={"origen": "test"},
            usuario=usuario,
            empresa=empresa,
        )

    def test_empleado_recibe_403(self):
        self.client.force_login(self.empleado)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_supervisor_recibe_403(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_admin_rrhh_ve_lista_de_su_empresa(self):
        log_a = self._crear_log(self.empresa_a, self.admin)
        log_b = self._crear_log(self.empresa_b, self.admin)
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        logs = list(response.context["logs"])
        pks = {log.pk for log in logs}
        self.assertIn(log_a.pk, pks)
        self.assertNotIn(log_b.pk, pks)
        self.assertTrue(all(log.empresa_id == self.empresa_a.pk for log in logs))
        self.assertContains(response, "Auditoría")
        self.assertContains(response, "origen")

    def test_superadmin_filtra_por_empresa_de_sesion(self):
        log_a = self._crear_log(self.empresa_a, self.admin)
        log_b = self._crear_log(self.empresa_b, self.admin)
        self.client.force_login(self.superadmin)
        session = self.client.session
        session["empresa_id"] = self.empresa_a.pk
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        pks = {log.pk for log in response.context["logs"]}
        self.assertIn(log_a.pk, pks)
        self.assertNotIn(log_b.pk, pks)

    def test_filtro_por_accion(self):
        self._crear_log(self.empresa_a, self.admin, accion=Accion.CREAR)
        self._crear_log(self.empresa_a, self.admin, accion=Accion.EDITAR)
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {"accion": Accion.EDITAR})
        self.assertEqual(response.status_code, 200)
        acciones = {log.accion for log in response.context["logs"]}
        self.assertEqual(acciones, {Accion.EDITAR})

    def test_tabla_incluye_detalle_json(self):
        self._crear_log(self.empresa_a, self.admin)
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertContains(response, "Ver payload")
        self.assertContains(response, "&quot;origen&quot;")
