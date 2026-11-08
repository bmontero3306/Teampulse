from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from empresas.api.serializers import EmpresaSerializer
from empresas.models import Empresa
from empresas.services import activar_empresa, inactivar_empresa, suspender_empresa


class CuitUnicoTests(TestCase):
    def test_no_se_duplica_cuit(self):
        make_empresa(cuit="20123456789")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_empresa(cuit="20123456789")

    def test_serializer_rechaza_cuit_duplicado_con_guiones(self):
        make_empresa(cuit="20123456789")
        request = RequestFactory().post("/api/v1/empresas/")
        request.user = Usuario(rol=Usuario.Rol.SUPERADMIN)
        serializer = EmpresaSerializer(
            data={
                "nombre": "Otra",
                "razon_social": "Otra S.A.",
                "cuit": "20-12345678-9",
                "email_contacto": "otra@test.com",
                "estado": Empresa.Estado.ACTIVA,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("cuit", serializer.errors)


class EstadoEmpresaTests(TestCase):
    def test_suspender_no_borra_datos_y_flag_estado(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa, rol="empleado")
        suspender_empresa(empresa)
        empresa.refresh_from_db()
        usuario.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.SUSPENDIDA)
        self.assertFalse(empresa.permite_login)
        self.assertTrue(Usuario.objects.filter(pk=usuario.pk).exists())
        self.assertEqual(usuario.empresa_id, empresa.pk)

    def test_activar_y_pasar_a_inactiva(self):
        empresa = make_empresa(estado=Empresa.Estado.SUSPENDIDA)
        self.assertFalse(empresa.permite_login)
        activar_empresa(empresa)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.ACTIVA)
        self.assertTrue(empresa.permite_login)
        inactivar_empresa(empresa)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.INACTIVA)
        self.assertFalse(empresa.permite_login)
        self.assertTrue(Empresa.objects.filter(pk=empresa.pk).exists())
