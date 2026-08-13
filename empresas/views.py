from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from app.mixins import RolRequiredMixin
from cuentas.models import Usuario
from empresas.forms import EmpresaFichaForm, EmpresaForm
from empresas.models import Empresa
from empresas.services import (
    activar_empresa,
    auditar_empresa,
    seleccionar_empresa,
    suspender_empresa,
)


class SuperadminEmpresaMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.SUPERADMIN]


class SuperadminOAdminRRHHMixin(RolRequiredMixin):
    roles_permitidos = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]


class EmpresaTenantQuerysetMixin:
    """Superadmin ve todas; admin RRHH solo la propia (request.empresa)."""

    def get_queryset(self):
        qs = Empresa.objects.all()
        user = self.request.user
        if getattr(user, "rol", None) == Usuario.Rol.SUPERADMIN:
            return qs
        empresa = getattr(self.request, "empresa", None) or getattr(user, "empresa", None)
        if getattr(user, "rol", None) == Usuario.Rol.ADMIN_RRHH and empresa is not None:
            return qs.filter(pk=empresa.pk)
        return qs.none()


class EmpresaListaView(SuperadminEmpresaMixin, ListView):
    model = Empresa
    template_name = "empresas/lista.html"
    context_object_name = "empresas"

    def get_queryset(self):
        qs = Empresa.objects.annotate(cantidad_usuarios=Count("usuarios")).order_by("nombre")
        estado = self.request.GET.get("estado")
        if estado in Empresa.Estado.values:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["estado_filtro"] = self.request.GET.get("estado", "")
        ctx["estados"] = Empresa.Estado.choices
        return ctx


class EmpresaCrearView(SuperadminEmpresaMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = "empresas/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nueva empresa"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        auditar_empresa(
            self.request,
            "empresa_alta",
            self.object,
            payload={"nombre": self.object.nombre, "cuit": self.object.cuit},
        )
        messages.success(self.request, "La empresa se creó correctamente.")
        return response

    def get_success_url(self):
        return reverse("empresas:detalle", args=[self.object.pk])


class EmpresaEditarView(SuperadminOAdminRRHHMixin, EmpresaTenantQuerysetMixin, UpdateView):
    model = Empresa
    template_name = "empresas/form.html"
    context_object_name = "empresa"

    def get_form_class(self):
        if getattr(self.request.user, "rol", None) == Usuario.Rol.ADMIN_RRHH:
            return EmpresaFichaForm
        return EmpresaForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Editar empresa"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        payload = {"campos": list(form.changed_data)}
        if "estado" in form.changed_data:
            payload["estado_anterior"] = form.initial.get("estado")
            payload["estado_nuevo"] = self.object.estado
        auditar_empresa(self.request, "empresa_edicion", self.object, payload=payload)
        messages.success(self.request, "La empresa se actualizó correctamente.")
        return response

    def get_success_url(self):
        return reverse("empresas:detalle", args=[self.object.pk])


class EmpresaDetalleView(SuperadminOAdminRRHHMixin, EmpresaTenantQuerysetMixin, DetailView):
    model = Empresa
    template_name = "empresas/detalle.html"
    context_object_name = "empresa"

    def get_queryset(self):
        return super().get_queryset().annotate(cantidad_usuarios=Count("usuarios"))


class EmpresaSuspenderView(SuperadminEmpresaMixin, View):
    def get(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        return render(request, "empresas/confirmar_suspender.html", {"empresa": empresa})

    def post(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        suspender_empresa(empresa, request)
        messages.success(
            request,
            "La empresa fue suspendida. Los datos se conservan; sus usuarios no podrán iniciar sesión.",
        )
        return redirect("empresas:detalle", pk=empresa.pk)


class EmpresaActivarView(SuperadminEmpresaMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        activar_empresa(empresa, request)
        messages.success(request, "La empresa se activó correctamente.")
        return redirect("empresas:detalle", pk=empresa.pk)


class EmpresaSeleccionarView(SuperadminEmpresaMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        seleccionar_empresa(request, empresa)
        messages.success(request, f"Contexto cambiado a {empresa.nombre}.")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect("empresas:lista")
