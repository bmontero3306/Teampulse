from rest_framework import serializers

from notificaciones.models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = (
            "id",
            "tipo",
            "titulo",
            "mensaje",
            "url",
            "leida",
            "created_at",
        )
