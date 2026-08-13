import json

from django.db import models

from app.querysets import EmpresaQuerySet
from auditoria.constants import ACCION_LABELS
from cuentas.models import Usuario


class AuditLog(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="empresa",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="usuario",
    )
    accion = models.CharField("acción", max_length=64)
    modelo = models.CharField("modelo", max_length=128, blank=True)
    object_id = models.CharField("id de objeto", max_length=64, blank=True)
    payload = models.JSONField("payload", default=dict, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("agente de usuario", max_length=512, blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    objects = EmpresaQuerySet.as_manager()

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "created_at"], name="auditoria_empresa_fecha_idx"),
            models.Index(fields=["modelo", "object_id"], name="auditoria_modelo_objeto_idx"),
        ]

    def __str__(self):
        return f"{self.accion} {self.modelo}#{self.object_id}".strip()

    @property
    def payload_pretty(self):
        return json.dumps(self.payload or {}, indent=2, ensure_ascii=False)

    @property
    def accion_display(self):
        return ACCION_LABELS.get(self.accion, self.accion)
