from django import forms

from app.forms_widgets import INPUT_CSS, SELECT_CSS
from empresas.models import Empresa
from empresas.validators import validar_cuit


class EmpresaForm(forms.ModelForm):
    """Alta/edición completa (superadmin)."""

    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "razon_social",
            "cuit",
            "email_contacto",
            "telefono",
            "direccion",
            "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "razon_social": forms.TextInput(attrs={"class": INPUT_CSS}),
            "cuit": forms.TextInput(
                attrs={
                    "class": INPUT_CSS,
                    "placeholder": "30-12345678-9",
                    "autocomplete": "off",
                }
            ),
            "email_contacto": forms.EmailInput(attrs={"class": INPUT_CSS}),
            "telefono": forms.TextInput(attrs={"class": INPUT_CSS}),
            "direccion": forms.TextInput(attrs={"class": INPUT_CSS}),
            "estado": forms.Select(attrs={"class": SELECT_CSS}),
        }
        help_texts = {
            "cuit": "11 dígitos, con o sin guiones (por ejemplo 30-12345678-9).",
        }

    def clean_cuit(self):
        cuit = validar_cuit(self.cleaned_data.get("cuit"))
        qs = Empresa.objects.filter(cuit=cuit)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una empresa con este CUIT.")
        return cuit


class EmpresaFichaForm(forms.ModelForm):
    """Admin RRHH: solo nombre y contacto; no desactiva ni cambia CUIT."""

    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "email_contacto",
            "telefono",
            "direccion",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "email_contacto": forms.EmailInput(attrs={"class": INPUT_CSS}),
            "telefono": forms.TextInput(attrs={"class": INPUT_CSS}),
            "direccion": forms.TextInput(attrs={"class": INPUT_CSS}),
        }
