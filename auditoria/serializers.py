from rest_framework import serializers

from auditoria.models import AuditLog


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
            "accion",
            "accion_display",
            "modelo",
            "object_id",
            "payload",
            "ip",
            "user_agent",
        )
