from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from cuentas.models import Usuario
from empresas.api.serializers import EmpresaSerializer
from empresas.models import Empresa
from empresas.validators import formatear_cuit, normalizar_cuit, validar_cuit


def _serializer(data, instance=None, rol=Usuario.Rol.SUPERADMIN):
    request = RequestFactory().post("/api/v1/empresas/")
    request.user = Usuario(rol=rol)
    return EmpresaSerializer(instance=instance, data=data, context={"request": request})


class ValidarCuitTests(TestCase):
    def test_acepta_11_digitos(self):
        self.assertEqual(validar_cuit("30712345678"), "30712345678")

    def test_acepta_con_guiones(self):
        self.assertEqual(validar_cuit("30-71234567-8"), "30712345678")

    def test_normaliza_espacios(self):
        self.assertEqual(normalizar_cuit(" 30-71234567-8 "), "30712345678")

    def test_rechaza_longitud_invalida(self):
        with self.assertRaises(ValidationError):
            validar_cuit("3071234567")

    def test_rechaza_letras(self):
        with self.assertRaises(ValidationError):
            validar_cuit("30-ABCDEFGH-1")

    def test_formatea_visualizacion(self):
        self.assertEqual(formatear_cuit("30712345678"), "30-71234567-8")

    def test_serializer_guarda_cuit_normalizado(self):
        serializer = _serializer(
            {
                "nombre": "Acme",
                "razon_social": "Acme S.A.",
                "cuit": "30-88888888-8",
                "email_contacto": "acme@test.com",
                "estado": Empresa.Estado.ACTIVA,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        empresa = serializer.save()
        self.assertEqual(empresa.cuit, "30888888888")
