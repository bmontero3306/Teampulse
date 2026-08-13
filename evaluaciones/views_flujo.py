from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from app.mixins import EmpresaRequiredMixin, RolRequiredMixin
from cuentas.models import Usuario
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.forms import (
    ObservacionConformidadForm,
    SupervisorCierreForm,
    autoevaluacion_formset,
    supervisor_formset,
)
from evaluaciones.models import Evaluacion
from evaluaciones.services import (
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
)

ROLES_FLUJO_PROPIO = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
    Usuario.Rol.EMPLEADO,
]
ROLES_SUPERVISOR = [Usuario.Rol.SUPERVISOR]


def _ip(request):
    meta = getattr(request, "META", {}) or {}
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return meta.get("REMOTE_ADDR") or None


def _get_evaluacion(request, pk):
    return get_object_or_404(
        Evaluacion.objects.for_empresa(request.empresa).select_related(
            "ciclo",
            "evaluado",
            "evaluador",
            "puesto",
            "plantilla",
        ),
        pk=pk,
    )


def _respuestas_desde_formset(formset, puntaje_field, comentario_field):
    datos = {}
    for form in formset.forms:
        if not form.instance.pk:
            continue
        cleaned = getattr(form, "cleaned_data", None) or {}
        datos[form.instance.pk] = {
            puntaje_field: cleaned.get(puntaje_field),
            comentario_field: cleaned.get(comentario_field) or "",
        }
    return datos


class FlujoPropioMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_FLUJO_PROPIO


class EquipoMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_SUPERVISOR


class MisEvaluacionesView(FlujoPropioMixin, ListView):
    template_name = "evaluaciones/mias.html"
    context_object_name = "evaluaciones"

    def get_queryset(self):
        return (
            Evaluacion.objects.for_empresa(self.request.empresa)
            .filter(evaluado=self.request.user)
            .select_related("ciclo", "puesto", "evaluador")
            .order_by("-ciclo__fecha_inicio", "pk")
        )


class AutoevaluacionView(FlujoPropioMixin, View):
    template_name = "evaluaciones/autoevaluacion.html"

    def get(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        self._autorizar(request, evaluacion)
        solo_lectura = evaluacion.estado not in (
            Evaluacion.Estado.PENDIENTE_AUTO,
            Evaluacion.Estado.AUTO_BORRADOR,
        )
        formset = autoevaluacion_formset(evaluacion)
        if solo_lectura:
            for form in formset.forms:
                for field in form.fields.values():
                    field.disabled = True
        return render(
            request,
            self.template_name,
            {
                "evaluacion": evaluacion,
                "formset": formset,
                "solo_lectura": solo_lectura,
            },
        )

    def post(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        self._autorizar(request, evaluacion)
        formset = autoevaluacion_formset(evaluacion, data=request.POST)
        enviar = request.POST.get("accion") == "enviar"
        if not formset.is_valid():
            messages.error(request, "Revisá los puntajes y comentarios.")
            return render(
                request,
                self.template_name,
                {
                    "evaluacion": evaluacion,
                    "formset": formset,
                    "solo_lectura": False,
                },
            )
        try:
            guardar_autoevaluacion(
                evaluacion,
                _respuestas_desde_formset(
                    formset, "puntaje_empleado", "comentario_empleado"
                ),
                enviar,
                request.user,
                request,
            )
        except EvaluacionesError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                self.template_name,
                {
                    "evaluacion": evaluacion,
                    "formset": formset,
                    "solo_lectura": False,
                },
            )
        if enviar:
            messages.success(request, "Autoevaluación enviada.")
            return redirect("evaluaciones:mias")
        messages.success(request, "Autoevaluación guardada como borrador.")
        return redirect("evaluaciones:auto", pk=evaluacion.pk)

    def _autorizar(self, request, evaluacion):
        if evaluacion.evaluado_id != request.user.pk:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")


class ResultadoView(FlujoPropioMixin, View):
    template_name = "evaluaciones/resultado.html"

    def get(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        if evaluacion.evaluado_id != request.user.pk:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        items = evaluacion.respuestas.select_related(
            "criterio", "criterio__competencia"
        ).order_by("criterio__orden", "pk")
        puede_firmar = (
            evaluacion.estado == Evaluacion.Estado.PENDIENTE_CONFORMIDAD
        )
        return render(
            request,
            self.template_name,
            {
                "evaluacion": evaluacion,
                "items": items,
                "puede_firmar": puede_firmar,
                "form_obs": ObservacionConformidadForm(),
            },
        )


class FirmarView(FlujoPropioMixin, View):
    def post(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        if evaluacion.evaluado_id != request.user.pk:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        accion = request.POST.get("accion")
        observacion = None
        if accion == "observacion":
            form = ObservacionConformidadForm(request.POST)
            if not form.is_valid() or not (form.cleaned_data.get("observacion") or "").strip():
                messages.error(
                    request,
                    "La observación de disconformidad es obligatoria.",
                )
                return redirect("evaluaciones:resultado", pk=evaluacion.pk)
            observacion = form.cleaned_data["observacion"]
        try:
            firmar_conformidad(
                evaluacion,
                request.user,
                _ip(request),
                observacion=observacion,
            )
        except EvaluacionesError as exc:
            messages.error(request, str(exc))
            return redirect("evaluaciones:resultado", pk=evaluacion.pk)
        if observacion:
            messages.success(
                request,
                "Se registró la observación de disconformidad.",
            )
        else:
            messages.success(request, "Conformidad firmada.")
        return redirect("evaluaciones:resultado", pk=evaluacion.pk)

    def get(self, request, pk):
        return redirect("evaluaciones:resultado", pk=pk)


class EquipoView(EquipoMixin, ListView):
    template_name = "evaluaciones/equipo.html"
    context_object_name = "evaluaciones"

    def get_queryset(self):
        return (
            Evaluacion.objects.for_empresa(self.request.empresa)
            .filter(evaluador=self.request.user)
            .select_related("ciclo", "evaluado", "puesto")
            .order_by("-ciclo__fecha_inicio", "evaluado__last_name", "pk")
        )


class SupervisarView(EquipoMixin, View):
    template_name = "evaluaciones/supervisar.html"

    def get(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        self._autorizar(request, evaluacion)
        puede_editar = evaluacion.estado in (
            Evaluacion.Estado.AUTO_COMPLETA,
            Evaluacion.Estado.SUPERVISOR_BORRADOR,
        )
        formset = supervisor_formset(evaluacion)
        form_cierre = SupervisorCierreForm(
            initial={"feedback_supervisor": evaluacion.feedback_supervisor}
        )
        if not puede_editar:
            for form in formset.forms:
                for field in form.fields.values():
                    field.disabled = True
            for field in form_cierre.fields.values():
                field.disabled = True
        return render(
            request,
            self.template_name,
            {
                "evaluacion": evaluacion,
                "formset": formset,
                "form_cierre": form_cierre,
                "puede_editar": puede_editar,
            },
        )

    def post(self, request, pk):
        evaluacion = _get_evaluacion(request, pk)
        self._autorizar(request, evaluacion)
        formset = supervisor_formset(evaluacion, data=request.POST)
        form_cierre = SupervisorCierreForm(request.POST)
        cerrar = request.POST.get("accion") == "cerrar"
        if not formset.is_valid() or not form_cierre.is_valid():
            messages.error(request, "Revisá los puntajes, comentarios y el feedback.")
            return render(
                request,
                self.template_name,
                {
                    "evaluacion": evaluacion,
                    "formset": formset,
                    "form_cierre": form_cierre,
                    "puede_editar": True,
                },
            )
        try:
            guardar_eval_supervisor(
                evaluacion,
                _respuestas_desde_formset(
                    formset, "puntaje_supervisor", "comentario_supervisor"
                ),
                form_cierre.cleaned_data.get("feedback_supervisor") or "",
                cerrar,
                request.user,
                request,
            )
        except EvaluacionesError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                self.template_name,
                {
                    "evaluacion": evaluacion,
                    "formset": formset,
                    "form_cierre": form_cierre,
                    "puede_editar": True,
                },
            )
        if cerrar:
            messages.success(request, "Evaluación de supervisor cerrada.")
            return redirect("evaluaciones:equipo")
        messages.success(request, "Evaluación de supervisor guardada.")
        return redirect("evaluaciones:supervisar", pk=evaluacion.pk)

    def _autorizar(self, request, evaluacion):
        if evaluacion.evaluador_id != request.user.pk:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        if evaluacion.estado in (
            Evaluacion.Estado.PENDIENTE_AUTO,
            Evaluacion.Estado.AUTO_BORRADOR,
        ):
            raise PermissionDenied(
                "El supervisor no puede evaluar antes de que se complete la autoevaluación."
            )
