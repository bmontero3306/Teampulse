from django.core.exceptions import ValidationError
from django.test import TestCase

from empresas.forms import EmpresaForm
from empresas.models import Empresa
from empresas.validators import formatear_cuit, normalizar_cuit, validar_cuit


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

    def test_form_guarda_cuit_normalizado(self):
        form = EmpresaForm(
            data={
                "nombre": "Acme",
                "razon_social": "Acme S.A.",
                "cuit": "30-88888888-8",
                "email_contacto": "acme@test.com",
                "estado": Empresa.Estado.ACTIVA,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        empresa = form.save()
        self.assertEqual(empresa.cuit, "30888888888")
