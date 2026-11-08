from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import make_empresa, make_usuario
from notificaciones.events import USUARIO_CREADO
from notificaciones.services import notificar


class ApiNotificacionesTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.usuario = make_usuario(self.empresa)
        self._auth(self.usuario)

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_lista_requiere_autenticacion(self):
        self.client.credentials()
        response = self.client.get("/api/v1/notificaciones/")
        self.assertEqual(response.status_code, 401)

    def test_lista_devuelve_campos_de_bandeja(self):
        notif = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Ir al panel",
            mensaje="Cuerpo",
            url="/dashboard/",
            empresa=self.empresa,
        )
        response = self.client.get("/api/v1/notificaciones/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["id"], notif.pk)
        self.assertEqual(item["titulo"], "Ir al panel")
        self.assertEqual(item["mensaje"], "Cuerpo")
        self.assertEqual(item["url"], "/dashboard/")
        self.assertEqual(item["tipo"], USUARIO_CREADO)
        self.assertFalse(item["leida"])
        self.assertIn("created_at", item)

    def test_marcar_leida(self):
        notif = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Ir al panel",
            mensaje="Cuerpo",
            url="/dashboard/",
            empresa=self.empresa,
        )
        response = self.client.post(f"/api/v1/notificaciones/{notif.pk}/leer/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["leida"])
        self.assertEqual(response.data["url"], "/dashboard/")
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
        response = self.client.post("/api/v1/notificaciones/leer-todas/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["detail"],
            "Todas las notificaciones se marcaron como leídas.",
        )
        self.assertEqual(self.usuario.notificaciones.no_leidas().count(), 0)
