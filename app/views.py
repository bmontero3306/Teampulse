from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from app.services import (
    accesos_rapidos_empleado,
    ciclo_activo,
    kpis_ciclo,
    pendientes_empleado,
    resumen_equipo,
)
from cuentas.models import Usuario
from empresas.models import Empresa


def home(request):
    return render(request, "app/home.html")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        empresa = getattr(self.request, "empresa", None)
        rol = getattr(user, "rol", None)
        ciclo = ciclo_activo(empresa)

        es_superadmin = rol == Usuario.Rol.SUPERADMIN
        es_admin = rol == Usuario.Rol.ADMIN_RRHH or (
            es_superadmin and empresa is not None
        )
        es_supervisor = rol == Usuario.Rol.SUPERVISOR
        es_empleado = rol in {Usuario.Rol.EMPLEADO, Usuario.Rol.SUPERVISOR}

        pendientes = (
            pendientes_empleado(user, empresa, ciclo) if es_empleado else []
        )
        equipo = resumen_equipo(user, empresa, ciclo) if es_supervisor else None

        context.update(
            {
                "ciclo_activo": ciclo,
                "kpis": kpis_ciclo(empresa, ciclo) if es_admin else None,
                "pendientes": pendientes,
                "accesos_rapidos": (
                    accesos_rapidos_empleado(pendientes) if es_empleado else []
                ),
                "equipo": equipo["evaluaciones"] if equipo else [],
                "equipo_resumen": equipo,
                "empresas_plataforma": (
                    list(Empresa.objects.all().order_by("nombre"))
                    if es_superadmin
                    else []
                ),
                "mostrar_pendientes": es_empleado,
                "mostrar_equipo": es_supervisor,
                "mostrar_kpis": es_admin,
                "mostrar_empresas": es_superadmin,
            }
        )
        return context
