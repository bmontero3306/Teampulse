"""Formularios de filtros del reporte ISO 9001 (WP7)."""

from django import forms

from app.forms_widgets import INPUT_CSS, SELECT_CSS
from cuentas.models import Usuario
from empresas.models import Empresa
from evaluaciones.models import CicloEvaluacion, Evaluacion
from organizacion.models import Area
from reportes.services import CONFORMIDAD_NO_FIRMADA

CONFORMIDAD_CHOICES = [
    ("", "Todos"),
    (Evaluacion.Estado.PENDIENTE_CONFORMIDAD, "Pendiente de conformidad"),
    (Evaluacion.Estado.CERRADA, "Firmada — conforme"),
    (Evaluacion.Estado.CERRADA_CON_OBS, "Firmada — con observación"),
    (CONFORMIDAD_NO_FIRMADA, "Sin firmar"),
]


class IsoFiltroForm(forms.Form):
    empresa = forms.ModelChoiceField(
        label="Empresa",
        required=False,
        queryset=Empresa.objects.none(),
        empty_label="Seleccioná una empresa",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    ciclo = forms.ModelChoiceField(
        label="Ciclo",
        required=False,
        queryset=CicloEvaluacion.objects.none(),
        empty_label="Todos",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    area = forms.ModelChoiceField(
        label="Área",
        required=False,
        queryset=Area.objects.none(),
        empty_label="Todas",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    estado = forms.ChoiceField(
        label="Estado de conformidad",
        required=False,
        choices=CONFORMIDAD_CHOICES,
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    fecha_desde = forms.DateField(
        label="Desde",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CSS}),
    )
    fecha_hasta = forms.DateField(
        label="Hasta",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CSS}),
    )

    def __init__(self, *args, empresa=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        es_superadmin = getattr(usuario, "rol", None) == Usuario.Rol.SUPERADMIN
        empresa_filtro = empresa

        if es_superadmin:
            self.fields["empresa"].queryset = Empresa.objects.order_by("nombre")
            if empresa is not None:
                self.fields["empresa"].initial = empresa.pk
            if self.is_bound:
                raw = self.data.get("empresa")
                if raw:
                    elegida = Empresa.objects.filter(pk=raw).first()
                    if elegida is not None:
                        empresa_filtro = elegida
        else:
            self.fields.pop("empresa")

        ciclos = CicloEvaluacion.objects.for_empresa(empresa_filtro).order_by(
            "-fecha_inicio", "nombre"
        )
        areas = Area.objects.for_empresa(empresa_filtro).order_by("nombre")
        self.fields["ciclo"].queryset = ciclos
        self.fields["area"].queryset = areas
