from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory, modelformset_factory

from app.forms_widgets import CHECKBOX_CSS, INPUT_CSS, SELECT_CSS
from cuentas.models import Usuario
from evaluaciones.models import (
    CicloEvaluacion,
    PlantillaCriterio,
    PlantillaEvaluacion,
    RespuestaItem,
)
from organizacion.models import Area, Competencia, Puesto

TEXTAREA_CSS = (
    "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 "
    "text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none "
    "focus:ring-1 focus:ring-sky-500 min-h-24"
)

SELECT_MULTIPLE_CSS = SELECT_CSS + " min-h-40"


class PlantillaEvaluacionForm(forms.ModelForm):
    puestos = forms.ModelMultipleChoiceField(
        queryset=Puesto.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": SELECT_MULTIPLE_CSS, "size": "8"}),
        label="Puestos asociados",
        help_text="Seleccioná uno o más puestos de esta empresa. Ctrl o Cmd para múltiples.",
    )

    class Meta:
        model = PlantillaEvaluacion
        fields = ["nombre", "tipo", "descripcion", "activa"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "tipo": forms.Select(attrs={"class": SELECT_CSS}),
            "descripcion": forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
            "activa": forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.empresa_id and empresa is not None:
            self.instance.empresa = empresa
        puestos_qs = Puesto.objects.for_empresa(empresa).filter(activo=True)
        if self.instance and self.instance.pk:
            puestos_qs = (
                Puesto.objects.for_empresa(empresa)
                .filter(Q(activo=True) | Q(pk__in=self.instance.puestos.values("pk")))
                .distinct()
            )
            self.fields["puestos"].initial = self.instance.puestos.all()
        self.fields["puestos"].queryset = puestos_qs.order_by("nombre")

    def clean_puestos(self):
        puestos = self.cleaned_data.get("puestos")
        if not puestos:
            return puestos
        if self.empresa and any(p.empresa_id != self.empresa.pk for p in puestos):
            raise forms.ValidationError(
                "No se pueden asociar puestos de otra empresa."
            )
        return puestos

    def save(self, commit=True):
        plantilla = super().save(commit=False)
        plantilla.empresa = self.empresa
        if commit:
            plantilla.save()
            plantilla.puestos.set(self.cleaned_data.get("puestos") or [])
        return plantilla


class PlantillaCriterioForm(forms.ModelForm):
    class Meta:
        model = PlantillaCriterio
        fields = [
            "competencia",
            "orden",
            "escala_min",
            "escala_max",
            "ponderacion",
            "comentario_empleado_obligatorio",
            "comentario_supervisor_obligatorio",
        ]
        widgets = {
            "competencia": forms.Select(attrs={"class": SELECT_CSS}),
            "orden": forms.NumberInput(attrs={"class": INPUT_CSS, "min": "1"}),
            "escala_min": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "escala_max": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "ponderacion": forms.NumberInput(
                attrs={"class": INPUT_CSS, "min": "0", "step": "0.01"}
            ),
            "comentario_empleado_obligatorio": forms.CheckboxInput(
                attrs={"class": CHECKBOX_CSS}
            ),
            "comentario_supervisor_obligatorio": forms.CheckboxInput(
                attrs={"class": CHECKBOX_CSS}
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        qs = Competencia.objects.for_empresa(empresa).filter(activa=True)
        if self.instance and self.instance.competencia_id:
            qs = Competencia.objects.for_empresa(empresa).filter(
                Q(activa=True) | Q(pk=self.instance.competencia_id)
            )
        self.fields["competencia"].queryset = qs.order_by("nombre")
        self.fields["competencia"].empty_label = "— Elegir competencia —"
        self.fields["orden"].required = False

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

    def clean(self):
        cleaned = super().clean()
        escala_min = cleaned.get("escala_min")
        escala_max = cleaned.get("escala_max")
        ponderacion = cleaned.get("ponderacion")
        if escala_min is not None and escala_max is not None and escala_min >= escala_max:
            self.add_error(
                "escala_max",
                "La escala mínima debe ser menor que la máxima.",
            )
        if ponderacion is not None and ponderacion < 0:
            self.add_error("ponderacion", "La ponderación no puede ser negativa.")
        return cleaned


class BasePlantillaCriterioFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].label = "Quitar"
            form.fields["DELETE"].widget.attrs["class"] = CHECKBOX_CSS

    def clean(self):
        super().clean()
        vistos = []
        orden_auto = 1
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE"):
                continue
            competencia = data.get("competencia")
            if not competencia:
                continue
            if competencia.pk in vistos:
                raise forms.ValidationError(
                    "No se puede usar la misma competencia más de una vez."
                )
            vistos.append(competencia.pk)
            if not data.get("orden"):
                form.cleaned_data["orden"] = orden_auto
                form.instance.orden = orden_auto
            orden_auto += 1


def plantilla_criterio_formset(empresa, **kwargs):
    FormSet = inlineformset_factory(
        PlantillaEvaluacion,
        PlantillaCriterio,
        form=PlantillaCriterioForm,
        formset=BasePlantillaCriterioFormSet,
        extra=1,
        can_delete=True,
        min_num=0,
        validate_min=False,
    )
    return FormSet(form_kwargs={"empresa": empresa}, prefix="criterios", **kwargs)


class CicloEvaluacionForm(forms.ModelForm):
    class Meta:
        model = CicloEvaluacion
        fields = [
            "nombre",
            "fecha_inicio",
            "fecha_cierre",
            "plantilla_default",
            "areas",
            "criterios_generales",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT_CSS}),
            "fecha_inicio": forms.DateInput(
                attrs={"class": INPUT_CSS, "type": "date"},
                format="%Y-%m-%d",
            ),
            "fecha_cierre": forms.DateInput(
                attrs={"class": INPUT_CSS, "type": "date"},
                format="%Y-%m-%d",
            ),
            "plantilla_default": forms.Select(attrs={"class": SELECT_CSS}),
            "areas": forms.SelectMultiple(
                attrs={"class": SELECT_CSS + " min-h-32", "size": "6"}
            ),
            "criterios_generales": forms.Textarea(
                attrs={"class": TEXTAREA_CSS, "rows": 4}
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_cierre"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_inicio"].localize = False
        self.fields["fecha_cierre"].localize = False
        self.fields["areas"].required = False
        self.fields["areas"].help_text = (
            "Si no seleccionás áreas, el ciclo incluye a toda la empresa."
        )
        self.fields["plantilla_default"].queryset = (
            PlantillaEvaluacion.objects.for_empresa(empresa)
            .filter(activa=True)
            .order_by("nombre")
        )
        if self.instance and self.instance.plantilla_default_id:
            self.fields["plantilla_default"].queryset = (
                PlantillaEvaluacion.objects.for_empresa(empresa)
                .filter(Q(activa=True) | Q(pk=self.instance.plantilla_default_id))
                .order_by("nombre")
            )
        self.fields["plantilla_default"].empty_label = "— Elegir plantilla —"
        areas_qs = Area.objects.for_empresa(empresa).filter(activa=True)
        if self.instance and self.instance.pk:
            areas_qs = (
                Area.objects.for_empresa(empresa)
                .filter(Q(activa=True) | Q(pk__in=self.instance.areas.values("pk")))
                .distinct()
            )
        self.fields["areas"].queryset = areas_qs.order_by("nombre")

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("fecha_inicio")
        cierre = cleaned.get("fecha_cierre")
        if inicio and cierre and cierre < inicio:
            self.add_error(
                "fecha_cierre",
                "La fecha de cierre no puede ser anterior al inicio.",
            )
        plantilla = cleaned.get("plantilla_default")
        if (
            plantilla
            and self.empresa is not None
            and plantilla.empresa_id != self.empresa.pk
        ):
            self.add_error(
                "plantilla_default",
                "La plantilla no pertenece a esta empresa.",
            )
        areas = cleaned.get("areas")
        if areas and self.empresa is not None:
            ajenas = [a for a in areas if a.empresa_id != self.empresa.pk]
            if ajenas:
                self.add_error("areas", "No se pueden asociar áreas de otra empresa.")
        return cleaned


class CicloReprogramarForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        widget=forms.DateInput(
            attrs={"class": INPUT_CSS, "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    fecha_cierre = forms.DateField(
        label="Fecha de cierre",
        widget=forms.DateInput(
            attrs={"class": INPUT_CSS, "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_inicio"].localize = False
        self.fields["fecha_cierre"].localize = False

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("fecha_inicio")
        cierre = cleaned.get("fecha_cierre")
        if inicio and cierre and cierre < inicio:
            self.add_error(
                "fecha_cierre",
                "La fecha de cierre no puede ser anterior al inicio.",
            )
        return cleaned


class AutoevaluacionItemForm(forms.ModelForm):
    class Meta:
        model = RespuestaItem
        fields = ["puntaje_empleado", "comentario_empleado"]
        widgets = {
            "puntaje_empleado": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "comentario_empleado": forms.Textarea(
                attrs={"class": TEXTAREA_CSS, "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criterio = getattr(self.instance, "criterio", None)
        if criterio is not None:
            self.fields["puntaje_empleado"].widget.attrs.update(
                {
                    "min": str(criterio.escala_min),
                    "max": str(criterio.escala_max),
                    "placeholder": f"{criterio.escala_min} – {criterio.escala_max}",
                }
            )
        self.fields["puntaje_empleado"].required = False
        self.fields["comentario_empleado"].required = False


class SupervisorItemForm(forms.ModelForm):
    class Meta:
        model = RespuestaItem
        fields = ["puntaje_supervisor", "comentario_supervisor"]
        widgets = {
            "puntaje_supervisor": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "comentario_supervisor": forms.Textarea(
                attrs={"class": TEXTAREA_CSS, "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criterio = getattr(self.instance, "criterio", None)
        if criterio is not None:
            self.fields["puntaje_supervisor"].widget.attrs.update(
                {
                    "min": str(criterio.escala_min),
                    "max": str(criterio.escala_max),
                    "placeholder": f"{criterio.escala_min} – {criterio.escala_max}",
                }
            )
        self.fields["puntaje_supervisor"].required = False
        self.fields["comentario_supervisor"].required = False


class SupervisorCierreForm(forms.Form):
    feedback_supervisor = forms.CharField(
        label="Feedback del supervisor",
        required=False,
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
    )
    habilitar_reunion = forms.BooleanField(
        label="Habilitar reunión de feedback",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
        help_text=(
            "Opcional. Si no la marcás, el empleado ve la comparación y firma "
            "con el feedback y las observaciones del sistema."
        ),
    )


class ObservacionConformidadForm(forms.Form):
    observacion = forms.CharField(
        label="Observación de disconformidad",
        required=False,
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
    )


class ReunionFeedbackForm(forms.Form):
    reunion_fecha = forms.DateTimeField(
        label="Fecha de la reunión",
        widget=forms.DateTimeInput(
            attrs={"class": INPUT_CSS, "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
    )
    reunion_notas = forms.CharField(
        label="Notas de la reunión",
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 4}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reunion_fecha"].localize = False


class ReasignarEvaluadorForm(forms.Form):
    evaluador = forms.ModelChoiceField(
        queryset=Usuario.objects.none(),
        empty_label="— Elegir evaluador —",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
        label="Evaluador",
    )

    def __init__(self, *args, evaluacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        from evaluaciones.services import candidatos_evaluador

        if evaluacion is not None:
            self.fields["evaluador"].queryset = candidatos_evaluador(evaluacion)


def autoevaluacion_formset(evaluacion, **kwargs):
    FormSet = modelformset_factory(
        RespuestaItem,
        form=AutoevaluacionItemForm,
        extra=0,
        can_delete=False,
    )
    qs = (
        RespuestaItem.objects.filter(evaluacion=evaluacion)
        .select_related("criterio", "criterio__competencia")
        .order_by("criterio__orden", "pk")
    )
    return FormSet(queryset=qs, prefix="items", **kwargs)


def supervisor_formset(evaluacion, **kwargs):
    FormSet = modelformset_factory(
        RespuestaItem,
        form=SupervisorItemForm,
        extra=0,
        can_delete=False,
    )
    qs = (
        RespuestaItem.objects.filter(evaluacion=evaluacion)
        .select_related("criterio", "criterio__competencia")
        .order_by("criterio__orden", "pk")
    )
    return FormSet(queryset=qs, prefix="items", **kwargs)
