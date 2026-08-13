from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TestCase


class MigracionesTests(TestCase):
    def test_auth_user_model_es_cuentas_usuario(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "cuentas.Usuario")

    def test_migraciones_aplican_sqlite_vacio(self):
        call_command("migrate", verbosity=0, interactive=False)
        tablas = connection.introspection.table_names()
        self.assertIn("cuentas_usuario", tablas)
        self.assertIn("empresas_empresa", tablas)
        self.assertNotIn("auth_user", tablas)
