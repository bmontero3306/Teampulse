from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.views.generic import TemplateView

from app.ayuda import grupos_paginas, pagina_por_slug, paginas_visibles
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


class AyudaMixin(LoginRequiredMixin):
    def _contexto_ayuda(self):
        user = self.request.user
        empresa = getattr(self.request, "empresa", None)
        paginas = paginas_visibles(user, empresa)
        return {
            "paginas_ayuda": paginas,
            "grupos_ayuda": grupos_paginas(user, empresa),
            "slugs_ayuda": {p["slug"] for p in paginas},
        }


class AyudaIndexView(AyudaMixin, TemplateView):
    template_name = "app/ayuda/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._contexto_ayuda())
        return context


class AyudaPaginaView(AyudaMixin, TemplateView):
    def get_template_names(self):
        slug = self.kwargs["slug"]
        return [f"app/ayuda/{slug}.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        pagina = pagina_por_slug(slug)
        user = self.request.user
        empresa = getattr(self.request, "empresa", None)
        visibles = paginas_visibles(user, empresa)
        if pagina is None:
            raise Http404("No encontramos esa guía.")
        if pagina not in visibles:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        slugs = [p["slug"] for p in visibles]
        indice = slugs.index(slug)
        context.update(self._contexto_ayuda())
        context["pagina"] = pagina
        context["pagina_anterior"] = visibles[indice - 1] if indice > 0 else None
        context["pagina_siguiente"] = (
            visibles[indice + 1] if indice < len(visibles) - 1 else None
        )
        return context
