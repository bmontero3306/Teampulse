from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from notificaciones.models import Notificacion


def _queryset_usuario(request):
    qs = Notificacion.objects.de_usuario(request.user)
    empresa = getattr(request, "empresa", None)
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    return qs


class ListaNotificacionesView(LoginRequiredMixin, ListView):
    template_name = "notificaciones/lista.html"
    context_object_name = "notificaciones"
    paginate_by = 20

    def get_queryset(self):
        return _queryset_usuario(self.request)


class LeerNotificacionView(LoginRequiredMixin, View):
    def get(self, request, pk):
        return self._marcar(request, pk)

    def post(self, request, pk):
        return self._marcar(request, pk)

    def _marcar(self, request, pk):
        notificacion = get_object_or_404(_queryset_usuario(request), pk=pk)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        destino = reverse("notificaciones:lista")
        if notificacion.url.startswith("/"):
            destino = notificacion.url
        return redirect(destino)


class LeerTodasNotificacionesView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("notificaciones:lista")

    def post(self, request):
        _queryset_usuario(request).no_leidas().update(leida=True)
        messages.success(request, "Todas las notificaciones se marcaron como leídas.")
        return redirect("notificaciones:lista")
