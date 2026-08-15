from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from app.mixins import EmpresaRequiredMixin, RolRequiredMixin
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from evaluaciones.forms import PlantillaEvaluacionForm, plantilla_criterio_formset
from evaluaciones.models import PlantillaEvaluacion
from evaluaciones.services import duplicar_plantilla
from organizacion.models import Competencia


ROLES_LECTURA = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
]
ROLES_CRUD = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]


def puede_editar_plantillas(user):
    return getattr(user, "rol", None) in ROLES_CRUD


class PlantillaLecturaMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_LECTURA

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_editar"] = puede_editar_plantillas(self.request.user)
        return ctx


class PlantillaCRUDMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_CRUD

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_editar"] = True
        return ctx


class PlantillaListView(PlantillaLecturaMixin, ListView):
    model = PlantillaEvaluacion
    template_name = "evaluaciones/plantillas_lista.html"
    context_object_name = "plantillas"

    def get_queryset(self):
        return (
            PlantillaEvaluacion.objects.for_empresa(self.request.empresa)
            .prefetch_related("puestos")
            .order_by("nombre")
        )


class PlantillaFormView(PlantillaCRUDMixin, View):
    template_name = "evaluaciones/plantilla_form.html"

    def get_object(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return get_object_or_404(
            PlantillaEvaluacion.objects.for_empresa(self.request.empresa),
            pk=pk,
        )

    def _context(self, form, formset, plantilla):
        puestos_qs = form.fields["puestos"].queryset
        return {
            "form": form,
            "formset": formset,
            "plantilla": plantilla,
            "puede_editar": True,
            "puestos_opciones": [
                {
                    "id": puesto.pk,
                    "nombre": puesto.nombre,
                    "area": puesto.area.nombre if puesto.area_id else "",
                }
                for puesto in puestos_qs
            ],
            "competencia_tipos": Competencia.Tipo.choices,
        }

    def get(self, request, pk=None):
        plantilla = self.get_object()
        form = PlantillaEvaluacionForm(empresa=request.empresa, instance=plantilla)
        formset = plantilla_criterio_formset(
            request.empresa, instance=form.instance
        )
        return render(
            request, self.template_name, self._context(form, formset, plantilla)
        )

    def post(self, request, pk=None):
        plantilla = self.get_object()
        form = PlantillaEvaluacionForm(
            request.POST, empresa=request.empresa, instance=plantilla
        )
        formset = plantilla_criterio_formset(
            request.empresa, data=request.POST, instance=form.instance
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                guardada = form.save(commit=False)
                guardada.empresa = request.empresa
                guardada.save()
                form.instance = guardada
                guardada.puestos.set(form.cleaned_data.get("puestos") or [])
                formset.instance = guardada
                formset.save()
            registrar_auditoria(
                request,
                accion="crear" if plantilla is None else "editar",
                instance=guardada,
            )
            messages.success(request, "Plantilla guardada correctamente.")
            return redirect("evaluaciones:plantillas")
        return render(
            request, self.template_name, self._context(form, formset, plantilla)
        )


class PlantillaDuplicarView(PlantillaCRUDMixin, View):
    def post(self, request, pk):
        original = get_object_or_404(
            PlantillaEvaluacion.objects.for_empresa(request.empresa),
            pk=pk,
        )
        copia = duplicar_plantilla(original)
        registrar_auditoria(request, accion="duplicar", instance=copia)
        messages.success(
            request,
            f"Se creó la plantilla «{copia.nombre}».",
        )
        return redirect("evaluaciones:plantilla_editar", pk=copia.pk)
