from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from notificaciones.models import Notificacion
from notificaciones.serializers import NotificacionSerializer
from notificaciones.views import _queryset_usuario


class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        return _queryset_usuario(self.request)

    @action(detail=True, methods=["post"])
    def leer(self, request, pk=None):
        notificacion = self.get_object()
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save(update_fields=["leida"])
        return Response(self.get_serializer(notificacion).data)

    @action(detail=False, methods=["post"], url_path="leer-todas")
    def leer_todas(self, request):
        self.get_queryset().filter(leida=False).update(leida=True)
        return Response({"detail": "Todas las notificaciones se marcaron como leídas."})
