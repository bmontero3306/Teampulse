from django.views.generic import ListView

from app.mixins import RolRequiredMixin
from app.querysets import for_empresa
from auditoria.forms import FiltroAuditLogForm
from auditoria.models import AuditLog
from cuentas.models import Usuario


class AuditLogListaView(RolRequiredMixin, ListView):
    model = AuditLog
    template_name = "auditoria/lista.html"
    context_object_name = "logs"
    paginate_by = 25
    roles_permitidos = [Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN]

    def get_queryset(self):
        qs = (
            AuditLog.objects.select_related("usuario", "empresa")
            .order_by("-created_at")
        )
        qs = for_empresa(qs, getattr(self.request, "empresa", None))

        form = self._filtro_form()
        if not form.is_valid():
            return qs

        datos = form.cleaned_data
        if datos.get("usuario"):
            qs = qs.filter(usuario=datos["usuario"])
        if datos.get("accion"):
            qs = qs.filter(accion=datos["accion"])
        if datos.get("modelo"):
            qs = qs.filter(modelo=datos["modelo"])
        if datos.get("fecha_desde"):
            qs = qs.filter(created_at__date__gte=datos["fecha_desde"])
        if datos.get("fecha_hasta"):
            qs = qs.filter(created_at__date__lte=datos["fecha_hasta"])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtro_form"] = self._filtro_form()
        return context

    def _filtro_form(self):
        if not hasattr(self, "_cached_filtro_form"):
            base = for_empresa(
                AuditLog.objects.all(),
                getattr(self.request, "empresa", None),
            )
            usuarios = (
                Usuario.objects.for_empresa(getattr(self.request, "empresa", None))
                .order_by("email")
            )
            acciones = list(
                base.exclude(accion="")
                .values_list("accion", flat=True)
                .distinct()
                .order_by("accion")
            )
            modelos = list(
                base.exclude(modelo="")
                .values_list("modelo", flat=True)
                .distinct()
                .order_by("modelo")
            )
            self._cached_filtro_form = FiltroAuditLogForm(
                self.request.GET or None,
                usuarios=usuarios,
                acciones=acciones,
                modelos=modelos,
            )
        return self._cached_filtro_form
