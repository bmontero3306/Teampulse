from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from app.tests.factories import make_empresa, make_usuario
from notificaciones.events import CICLO_ACTIVADO, USUARIO_CREADO
from notificaciones.models import Notificacion
from notificaciones.services import notificar


class NotificarServiceTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.usuario = make_usuario(self.empresa, first_name="Ana")

    def test_crea_notificacion_e_outbox(self):
        notif = notificar(
            tipo=USUARIO_CREADO,
            usuario=self.usuario,
            titulo="Cuenta lista",
            mensaje="Ya podés ingresar.",
            url="/dashboard/",
            empresa=self.empresa,
        )
        self.assertIsNotNone(notif)
        self.assertEqual(Notificacion.objects.count(), 1)
        self.assertEqual(notif.usuario, self.usuario)
        self.assertEqual(notif.empresa, self.empresa)
        self.assertFalse(notif.leida)
        self.assertTrue(notif.email_enviado)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.usuario.email])
        self.assertEqual(mail.outbox[0].subject, "Cuenta lista")

    def test_evento_resuelve_titulo_y_mensaje(self):
        notif = notificar(
            evento=CICLO_ACTIVADO,
            usuario=self.usuario,
            contexto={"ciclo": "Q1 2026", "fecha_cierre": "30/04/2026"},
        )
        self.assertEqual(notif.tipo, CICLO_ACTIVADO)
        self.assertIn("Q1 2026", notif.mensaje)
        self.assertIn("30/04/2026", notif.mensaje)
        self.assertTrue(notif.titulo)

    def test_contexto_posicional_como_tercer_arg(self):
        notif = notificar(
            USUARIO_CREADO,
            self.usuario,
            {"nombre": "Ana", "empresa": self.empresa.nombre},
        )
        self.assertIn("Ana", notif.mensaje)
        self.assertEqual(len(mail.outbox), 1)

    def test_mail_falla_no_crashea_y_deja_email_enviado_false(self):
        with patch(
            "notificaciones.services.EmailMultiAlternatives.send",
            side_effect=OSError("smtp caído"),
        ):
            notif = notificar(
                tipo=USUARIO_CREADO,
                usuario=self.usuario,
                titulo="Hola",
                mensaje="Cuerpo",
                empresa=self.empresa,
            )
        self.assertIsNotNone(notif)
        notif.refresh_from_db()
        self.assertFalse(notif.email_enviado)
        self.assertEqual(Notificacion.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
