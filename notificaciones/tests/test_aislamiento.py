from django.test import TestCase
from django.urls import reverse

from app.tests.factories import make_empresa, make_usuario
from notificaciones.events import USUARIO_CREADO
from notificaciones.models import Notificacion
from notificaciones.services import notificar


class AislamientoNotificacionesTests(TestCase):
    def setUp(self):
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.usuario_a = make_usuario(self.empresa_a)
        self.usuario_b = make_usuario(self.empresa_b)
        self.otro_a = make_usuario(self.empresa_a)
        self.notif_a = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario_a,
            titulo="Solo A",
            mensaje="Privada de A",
            empresa=self.empresa_a,
        )
        self.notif_b = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario_b,
            titulo="Solo B",
            mensaje="Privada de B",
            empresa=self.empresa_b,
        )
        self.notif_otro = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.otro_a,
            titulo="Otro de A",
            mensaje="De un compañero",
            empresa=self.empresa_a,
        )

    def test_lista_solo_propias(self):
        self.client.force_login(self.usuario_a)
        response = self.client.get(reverse("notificaciones:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solo A")
        self.assertNotContains(response, "Solo B")
        self.assertNotContains(response, "Otro de A")

    def test_no_lee_notificacion_de_otro_usuario(self):
        self.client.force_login(self.usuario_a)
        response = self.client.get(
            reverse("notificaciones:leer", kwargs={"pk": self.notif_otro.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.notif_otro.refresh_from_db()
        self.assertFalse(self.notif_otro.leida)

    def test_no_lee_notificacion_de_otra_empresa(self):
        self.client.force_login(self.usuario_a)
        response = self.client.get(
            reverse("notificaciones:leer", kwargs={"pk": self.notif_b.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_queryset_for_empresa(self):
        de_a = Notificacion.objects.for_empresa(self.empresa_a)
        self.assertEqual(de_a.count(), 2)
        self.assertNotIn(self.notif_b, de_a)
