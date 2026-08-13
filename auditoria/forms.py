from django import forms

from app.forms_widgets import INPUT_CSS, SELECT_CSS
from auditoria.constants import ACCION_LABELS
from cuentas.models import Usuario


class FiltroAuditLogForm(forms.Form):
    usuario = forms.ModelChoiceField(
        label="Usuario",
        required=False,
        queryset=Usuario.objects.none(),
        empty_label="Todos",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    accion = forms.CharField(
        label="Acción",
        required=False,
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    modelo = forms.CharField(
        label="Modelo",
        required=False,
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

    def __init__(self, *args, usuarios=None, acciones=None, modelos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios if usuarios is not None else Usuario.objects.none()
        self.fields["accion"].widget.choices = [("", "Todas")] + [
            (valor, ACCION_LABELS.get(valor, valor)) for valor in (acciones or [])
        ]
        self.fields["modelo"].widget.choices = [("", "Todos")] + [
            (valor, valor) for valor in (modelos or [])
        ]
