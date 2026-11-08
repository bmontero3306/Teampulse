from rest_framework import serializers

from auditoria.models import AuditLog
from cuentas.models import Usuario


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.CharField(source="usuario.email", read_only=True, default=None)
    accion_display = serializers.CharField(read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "created_at",
            "usuario",
            "usuario_email",
            "empresa",
            "accion",
            "accion_display",
            "modelo",
            "object_id",
            "payload",
            "ip",
            "user_agent",
        )


class AuditLogQuerySerializer(serializers.Serializer):
    usuario = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.none(),
        required=False,
        allow_null=True,
    )
    accion = serializers.CharField(required=False, allow_blank=True)
    modelo = serializers.CharField(required=False, allow_blank=True)
    fecha_desde = serializers.DateField(required=False, allow_null=True)
    fecha_hasta = serializers.DateField(required=False, allow_null=True)

    def __init__(self, *args, usuarios=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuarios is not None:
            self.fields["usuario"].queryset = usuarios
