from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario
from notificaciones.events import USUARIO_CREADO
from notificaciones.services import notificar


class VistasNotificacionesTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.usuario = make_usuario(self.empresa)

    def test_lista_requiere_login(self):
        response = self.client.get(reverse("notificaciones:lista"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_marcar_leida_y_redirige_a_url(self):
        notif = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Ir al panel",
            mensaje="Cuerpo",
            url="/dashboard/",
            empresa=self.empresa,
        )
        self.client.force_login(self.usuario)
        response = self.client.get(
            reverse("notificaciones:leer", kwargs={"pk": notif.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")
        notif.refresh_from_db()
        self.assertTrue(notif.leida)

    def test_marcar_todas_leidas(self):
        notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Uno",
            mensaje="a",
            empresa=self.empresa,
        )
        notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Dos",
            mensaje="b",
            empresa=self.empresa,
        )
        self.client.force_login(self.usuario)
        response = self.client.post(reverse("notificaciones:leer_todas"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.usuario.notificaciones.no_leidas().count(),
            0,
        )

    def test_context_processor_cuenta_no_leidas(self):
        notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Nueva",
            mensaje="x",
            empresa=self.empresa,
        )
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("app:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["notificaciones_no_leidas"], 1)
        self.assertContains(response, reverse("notificaciones:lista"))
