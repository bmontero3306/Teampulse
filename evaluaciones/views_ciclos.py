from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from app.mixins import EmpresaRequiredMixin, RolRequiredMixin
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.forms import CicloEvaluacionForm, CicloReprogramarForm
from evaluaciones.models import CicloEvaluacion, Evaluacion
from evaluaciones.services import (
    activar_ciclo,
    cancelar_ciclo,
    pausar_ciclo,
    reprogramar_ciclo,
)

ROLES_LECTURA = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
]
ROLES_CRUD = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]


def puede_gestionar_ciclos(user):
    return getattr(user, "rol", None) in ROLES_CRUD


class CicloLecturaMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_LECTURA

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_gestionar"] = puede_gestionar_ciclos(self.request.user)
        return ctx


class CicloCRUDMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_CRUD

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_gestionar"] = True
        return ctx


def _get_ciclo(request, pk):
    return get_object_or_404(
        CicloEvaluacion.objects.for_empresa(request.empresa),
        pk=pk,
    )


class CicloListView(CicloLecturaMixin, ListView):
    model = CicloEvaluacion
    template_name = "evaluaciones/ciclos_lista.html"
    context_object_name = "ciclos"

    def get_queryset(self):
        return (
            CicloEvaluacion.objects.for_empresa(self.request.empresa)
            .select_related("plantilla_default")
            .annotate(
                total_evals=Count("evaluaciones", distinct=True),
                sin_evaluador_count=Count(
                    "evaluaciones",
                    filter=Q(evaluaciones__sin_evaluador=True),
                    distinct=True,
                ),
            )
            .order_by("-fecha_inicio", "nombre")
        )


class CicloCrearView(CicloCRUDMixin, View):
    template_name = "evaluaciones/ciclo_form.html"

    def get(self, request):
        form = CicloEvaluacionForm(empresa=request.empresa)
        return render(request, self.template_name, {"form": form, "ciclo": None})

    def post(self, request):
        form = CicloEvaluacionForm(request.POST, empresa=request.empresa)
        if form.is_valid():
            ciclo = form.save(commit=False)
            ciclo.empresa = request.empresa
            ciclo.estado = CicloEvaluacion.Estado.BORRADOR
            ciclo.save()
            form.save_m2m()
            registrar_auditoria(request, accion="crear", instance=ciclo)
            messages.success(request, "Ciclo creado en borrador.")
            return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)
        return render(request, self.template_name, {"form": form, "ciclo": None})


class CicloDetalleView(CicloLecturaMixin, View):
    template_name = "evaluaciones/ciclo_detalle.html"

    def get(self, request, pk):
        ciclo = _get_ciclo(request, pk)
        return render(request, self.template_name, self._context(request, ciclo))

    def post(self, request, pk):
        if not puede_gestionar_ciclos(request.user):
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        ciclo = _get_ciclo(request, pk)
        if ciclo.estado != CicloEvaluacion.Estado.BORRADOR:
            messages.error(request, "Solo se puede editar un ciclo en borrador.")
            return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)
        form = CicloEvaluacionForm(
            request.POST, empresa=request.empresa, instance=ciclo
        )
        if form.is_valid():
            guardado = form.save()
            registrar_auditoria(request, accion="editar", instance=guardado)
            messages.success(request, "Ciclo actualizado.")
            return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)
        ctx = self._context(request, ciclo)
        ctx["form"] = form
        return render(request, self.template_name, ctx)

    def _context(self, request, ciclo):
        evaluaciones = (
            ciclo.evaluaciones.select_related("evaluado", "evaluador", "puesto")
            .order_by("evaluado__last_name", "evaluado__first_name", "pk")
        )
        total = evaluaciones.count()
        auto = evaluaciones.filter(
            estado__in=[
                Evaluacion.Estado.AUTO_COMPLETA,
                Evaluacion.Estado.SUPERVISOR_BORRADOR,
                Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
                Evaluacion.Estado.CERRADA,
                Evaluacion.Estado.CERRADA_CON_OBS,
            ]
        ).count()
        supervisor = evaluaciones.filter(
            estado__in=[
                Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
                Evaluacion.Estado.CERRADA,
                Evaluacion.Estado.CERRADA_CON_OBS,
            ]
        ).count()
        firmadas = evaluaciones.filter(
            estado__in=[Evaluacion.Estado.CERRADA, Evaluacion.Estado.CERRADA_CON_OBS]
        ).count()
        sin_evaluador = list(evaluaciones.filter(sin_evaluador=True))
        form = None
        if (
            puede_gestionar_ciclos(request.user)
            and ciclo.estado == CicloEvaluacion.Estado.BORRADOR
        ):
            form = CicloEvaluacionForm(empresa=request.empresa, instance=ciclo)
        return {
            "ciclo": ciclo,
            "evaluaciones": evaluaciones,
            "puede_gestionar": puede_gestionar_ciclos(request.user),
            "form": form,
            "progreso": {
                "total": total,
                "auto": auto,
                "supervisor": supervisor,
                "firmadas": firmadas,
                "sin_evaluador": len(sin_evaluador),
            },
            "sin_evaluador_list": sin_evaluador,
        }


class CicloTransicionView(CicloCRUDMixin, View):
    accion = None
    titulo = ""
    mensaje = ""
    confirmacion = ""
    peligro = False

    def get(self, request, pk):
        ciclo = _get_ciclo(request, pk)
        return render(
            request,
            "evaluaciones/ciclo_confirmar.html",
            {
                "ciclo": ciclo,
                "titulo": self.titulo,
                "mensaje": self.mensaje.format(ciclo=ciclo.nombre),
                "confirmacion": self.confirmacion,
                "peligro": self.peligro,
            },
        )

    def post(self, request, pk):
        ciclo = _get_ciclo(request, pk)
        try:
            if self.accion == "activar":
                ciclo, sin_evaluador = activar_ciclo(ciclo, request.user, request)
                messages.success(
                    request,
                    "El ciclo se activó y se generaron las evaluaciones.",
                )
                if sin_evaluador:
                    messages.warning(
                        request,
                        f"{len(sin_evaluador)} participante(s) sin evaluador asignado.",
                    )
            elif self.accion == "pausar":
                pausar_ciclo(ciclo, request.user, request)
                messages.success(request, "El ciclo fue pausado.")
            elif self.accion == "cancelar":
                cancelar_ciclo(ciclo, request.user, request)
                messages.success(request, "El ciclo fue cancelado.")
        except EvaluacionesError as exc:
            messages.error(request, str(exc))
            return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)
        return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)


class CicloActivarView(CicloTransicionView):
    accion = "activar"
    titulo = "Activar ciclo"
    mensaje = "Vas a activar el ciclo «{ciclo}». Se generarán las evaluaciones de los empleados con puesto."
    confirmacion = "Activar ciclo"


class CicloPausarView(CicloTransicionView):
    accion = "pausar"
    titulo = "Pausar ciclo"
    mensaje = "Vas a pausar el ciclo «{ciclo}». El historial se conserva."
    confirmacion = "Pausar ciclo"


class CicloCancelarView(CicloTransicionView):
    accion = "cancelar"
    titulo = "Cancelar ciclo"
    mensaje = (
        "Vas a cancelar el ciclo «{ciclo}». No se borra el historial, "
        "pero se bloquean nuevas ediciones."
    )
    confirmacion = "Cancelar ciclo"
    peligro = True


class CicloReprogramarView(CicloCRUDMixin, View):
    template_name = "evaluaciones/ciclo_reprogramar.html"

    def get(self, request, pk):
        ciclo = _get_ciclo(request, pk)
        form = CicloReprogramarForm(
            initial={
                "fecha_inicio": ciclo.fecha_inicio,
                "fecha_cierre": ciclo.fecha_cierre,
            }
        )
        return render(
            request, self.template_name, {"ciclo": ciclo, "form": form}
        )

    def post(self, request, pk):
        ciclo = _get_ciclo(request, pk)
        form = CicloReprogramarForm(request.POST)
        if form.is_valid():
            try:
                reprogramar_ciclo(
                    ciclo,
                    form.cleaned_data["fecha_inicio"],
                    form.cleaned_data["fecha_cierre"],
                    request.user,
                    request,
                )
            except EvaluacionesError as exc:
                messages.error(request, str(exc))
                return render(
                    request, self.template_name, {"ciclo": ciclo, "form": form}
                )
            messages.success(request, "Las fechas del ciclo se actualizaron.")
            return redirect("evaluaciones:ciclo_detalle", pk=ciclo.pk)
        return render(
            request, self.template_name, {"ciclo": ciclo, "form": form}
        )
