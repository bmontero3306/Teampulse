from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from app.mixins import EmpresaRequiredMixin, RolRequiredMixin
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from organizacion.forms import (
    AreaForm,
    CompetenciaForm,
    PuestoForm,
    puesto_competencia_formset,
)
from organizacion.models import Area, Competencia, Puesto
from organizacion.services import query_organigrama


ROLES_LECTURA = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
    Usuario.Rol.EMPLEADO,
]
ROLES_CRUD = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]


def puede_editar_organizacion(user):
    return getattr(user, "rol", None) in ROLES_CRUD


def _puesto_usuario(user):
    return getattr(user, "puesto", None)


def _area_usuario(user):
    area = getattr(user, "area", None)
    if area is not None:
        return area
    puesto = _puesto_usuario(user)
    return getattr(puesto, "area", None) if puesto is not None else None


class OrganizacionLecturaMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_LECTURA

    def puede_editar(self):
        return puede_editar_organizacion(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_editar"] = self.puede_editar()
        return ctx


class OrganizacionCRUDMixin(EmpresaRequiredMixin, RolRequiredMixin):
    roles_permitidos = ROLES_CRUD

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["puede_editar"] = True
        return ctx


def _filtrar_puestos_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activo=True)
        return qs
    puesto = _puesto_usuario(user)
    if puesto is None:
        return qs.none()
    return qs.filter(pk=puesto.pk)


def _filtrar_areas_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activa=True)
        return qs
    area = _area_usuario(user)
    if area is None:
        return qs.none()
    return qs.filter(pk=area.pk)


def _filtrar_competencias_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activa=True)
        return qs
    puesto = _puesto_usuario(user)
    if puesto is None:
        return qs.none()
    return qs.filter(puesto_competencias__puesto=puesto).distinct()


class OrganigramaView(OrganizacionLecturaMixin, TemplateView):
    template_name = "organizacion/organigrama.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        empresa = self.request.empresa
        raiz = None
        if user.rol == Usuario.Rol.EMPLEADO:
            raiz = _puesto_usuario(user)
            if raiz is None:
                ctx["raices"] = []
                ctx["sin_puesto"] = True
                return ctx
        ctx["sin_puesto"] = False
        ctx["raices"] = query_organigrama(empresa, solo_activos=True, raiz=raiz)
        return ctx


class PuestoListView(OrganizacionLecturaMixin, ListView):
    model = Puesto
    template_name = "organizacion/puestos_lista.html"
    context_object_name = "puestos"

    def get_queryset(self):
        qs = (
            Puesto.objects.for_empresa(self.request.empresa)
            .select_related("area", "puesto_superior")
            .order_by("nombre")
        )
        return _filtrar_puestos_lectura(qs, self.request.user)


class AreaListView(OrganizacionLecturaMixin, ListView):
    model = Area
    template_name = "organizacion/areas_lista.html"
    context_object_name = "areas"

    def get_queryset(self):
        qs = (
            Area.objects.for_empresa(self.request.empresa)
            .select_related("area_padre")
            .order_by("nombre")
        )
        return _filtrar_areas_lectura(qs, self.request.user)


class CompetenciaListView(OrganizacionLecturaMixin, ListView):
    model = Competencia
    template_name = "organizacion/competencias_lista.html"
    context_object_name = "competencias"

    def get_queryset(self):
        qs = Competencia.objects.for_empresa(self.request.empresa).order_by("nombre")
        return _filtrar_competencias_lectura(qs, self.request.user)


class AreaFormView(OrganizacionCRUDMixin, View):
    template_name = "organizacion/area_form.html"

    def get_object(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return get_object_or_404(
            Area.objects.for_empresa(self.request.empresa), pk=pk
        )

    def get(self, request, pk=None):
        area = self.get_object()
        form = AreaForm(empresa=request.empresa, instance=area)
        return render(
            request,
            self.template_name,
            {"form": form, "area": area, "puede_editar": True},
        )

    def post(self, request, pk=None):
        area = self.get_object()
        form = AreaForm(request.POST, empresa=request.empresa, instance=area)
        if form.is_valid():
            guardada = form.save()
            registrar_auditoria(
                request,
                accion="crear" if area is None else "editar",
                instance=guardada,
            )
            messages.success(request, "Área guardada correctamente.")
            return redirect("organizacion:areas")
        return render(
            request,
            self.template_name,
            {"form": form, "area": area, "puede_editar": True},
        )


class CompetenciaFormView(OrganizacionCRUDMixin, View):
    template_name = "organizacion/competencia_form.html"

    def get_object(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return get_object_or_404(
            Competencia.objects.for_empresa(self.request.empresa), pk=pk
        )

    def get(self, request, pk=None):
        competencia = self.get_object()
        form = CompetenciaForm(empresa=request.empresa, instance=competencia)
        return render(
            request,
            self.template_name,
            {"form": form, "competencia": competencia, "puede_editar": True},
        )

    def post(self, request, pk=None):
        competencia = self.get_object()
        form = CompetenciaForm(
            request.POST, empresa=request.empresa, instance=competencia
        )
        if form.is_valid():
            guardada = form.save()
            registrar_auditoria(
                request,
                accion="crear" if competencia is None else "editar",
                instance=guardada,
            )
            messages.success(request, "Competencia guardada correctamente.")
            return redirect("organizacion:competencias")
        return render(
            request,
            self.template_name,
            {"form": form, "competencia": competencia, "puede_editar": True},
        )


def _suma_ponderaciones(formset):
    total = Decimal("0")
    for form in formset.forms:
        data = getattr(form, "cleaned_data", None)
        if not data or data.get("DELETE"):
            continue
        if not data.get("competencia"):
            continue
        total += data.get("ponderacion") or Decimal("0")
    return total


class PuestoFormView(OrganizacionCRUDMixin, View):
    template_name = "organizacion/puesto_form.html"

    def get_object(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return get_object_or_404(
            Puesto.objects.for_empresa(self.request.empresa), pk=pk
        )

    def _context(self, form, formset, puesto):
        return {
            "form": form,
            "formset": formset,
            "puesto": puesto,
            "puede_editar": True,
        }

    def get(self, request, pk=None):
        puesto = self.get_object()
        form = PuestoForm(empresa=request.empresa, instance=puesto)
        formset = puesto_competencia_formset(
            request.empresa, instance=form.instance
        )
        return render(request, self.template_name, self._context(form, formset, puesto))

    def post(self, request, pk=None):
        puesto = self.get_object()
        form = PuestoForm(request.POST, empresa=request.empresa, instance=puesto)
        formset = puesto_competencia_formset(
            request.empresa, data=request.POST, instance=form.instance
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                guardado = form.save()
                formset.instance = guardado
                formset.save()
            registrar_auditoria(
                request,
                accion="crear" if puesto is None else "editar",
                instance=guardado,
            )
            total = _suma_ponderaciones(formset)
            if total != Decimal("100") and total > 0:
                suma = format(total.quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")
                messages.warning(
                    request,
                    f"La suma de ponderaciones es {suma}%. Se recomienda 100%, "
                    "pero el puesto se guardó igual.",
                )
            messages.success(request, "Puesto guardado correctamente.")
            return redirect("organizacion:puestos")
        return render(
            request, self.template_name, self._context(form, formset, puesto)
        )
