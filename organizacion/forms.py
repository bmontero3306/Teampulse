from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from app.forms_widgets import CHECKBOX_CSS, INPUT_CSS, SELECT_CSS
from organizacion.models import Area, Competencia, Puesto, PuestoCompetencia
from organizacion.services import (
    JerarquiaCircularError,
    validar_jerarquia_areas,
    validar_jerarquia_puestos,
)

TEXTAREA_CSS = (
    "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 "
    "text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none "
    "focus:ring-1 focus:ring-sky-500 min-h-24"
)


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ["nombre", "area_padre", "activa"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "area_padre": forms.Select(attrs={"class": SELECT_CSS}),
            "activa": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.empresa_id and empresa is not None:
            self.instance.empresa = empresa
        qs = Area.objects.for_empresa(empresa)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields["area_padre"].queryset = qs
        self.fields["area_padre"].required = False
        self.fields["area_padre"].empty_label = "— Sin área padre —"

    def clean_area_padre(self):
        padre = self.cleaned_data.get("area_padre")
        try:
            validar_jerarquia_areas(self.instance, padre)
        except JerarquiaCircularError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return padre

    def save(self, commit=True):
        area = super().save(commit=False)
        area.empresa = self.empresa
        if commit:
            area.save()
        return area


class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = ["nombre", "descripcion", "area", "puesto_superior", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "descripcion": forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
            "area": forms.Select(attrs={"class": SELECT_CSS}),
            "puesto_superior": forms.Select(attrs={"class": SELECT_CSS}),
            "activo": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.empresa_id and empresa is not None:
            self.instance.empresa = empresa
        self.fields["area"].queryset = Area.objects.for_empresa(empresa)
        self.fields["area"].required = False
        self.fields["area"].empty_label = "— Sin área —"
        superiores = Puesto.objects.for_empresa(empresa)
        if self.instance and self.instance.pk:
            superiores = superiores.exclude(pk=self.instance.pk)
        self.fields["puesto_superior"].queryset = superiores
        self.fields["puesto_superior"].required = False
        self.fields["puesto_superior"].empty_label = "— Sin puesto superior —"

    def clean_puesto_superior(self):
        superior = self.cleaned_data.get("puesto_superior")
        try:
            validar_jerarquia_puestos(self.instance, superior)
        except JerarquiaCircularError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return superior

    def save(self, commit=True):
        puesto = super().save(commit=False)
        puesto.empresa = self.empresa
        if commit:
            puesto.save()
        return puesto


class CompetenciaForm(forms.ModelForm):
    class Meta:
        model = Competencia
        fields = ["nombre", "descripcion", "tipo", "activa"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "descripcion": forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
            "tipo": forms.Select(attrs={"class": SELECT_CSS}),
            "activa": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.empresa_id and empresa is not None:
            self.instance.empresa = empresa

    def save(self, commit=True):
        competencia = super().save(commit=False)
        competencia.empresa = self.empresa
        if commit:
            competencia.save()
        return competencia


class PuestoCompetenciaForm(forms.ModelForm):
    class Meta:
        model = PuestoCompetencia
        fields = ["competencia", "ponderacion"]
        widgets = {
            "competencia": forms.Select(attrs={"class": SELECT_CSS}),
            "ponderacion": forms.NumberInput(
                attrs={
                    "class": INPUT_CSS,
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        qs = Competencia.objects.for_empresa(empresa)
        self.fields["competencia"].queryset = qs
        self.fields["competencia"].empty_label = "— Elegir competencia —"

    def clean_competencia(self):
        competencia = self.cleaned_data.get("competencia")
        if (
            competencia
            and self.empresa is not None
            and competencia.empresa_id != self.empresa.pk
        ):
            raise forms.ValidationError(
                "La competencia no pertenece a esta empresa."
            )
        return competencia


class BasePuestoCompetenciaFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].label = "Quitar"
            form.fields["DELETE"].widget.attrs["class"] = CHECKBOX_CSS

    def clean(self):
        super().clean()
        vistos = []
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE"):
                continue
            competencia = data.get("competencia")
            if not competencia:
                continue
            if competencia.pk in vistos:
                raise forms.ValidationError(
                    "No se puede asignar la misma competencia más de una vez."
                )
            vistos.append(competencia.pk)


def puesto_competencia_formset(empresa, **kwargs):
    FormSet = inlineformset_factory(
        Puesto,
        PuestoCompetencia,
        form=PuestoCompetenciaForm,
        formset=BasePuestoCompetenciaFormSet,
        extra=1,
        can_delete=True,
        min_num=0,
        validate_min=False,
    )
    return FormSet(form_kwargs={"empresa": empresa}, prefix="competencias", **kwargs)
