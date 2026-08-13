from django.db import models

from notificaciones.events import TIPO_CHOICES


class NotificacionQuerySet(models.QuerySet):
    def for_empresa(self, empresa):
        if empresa is None:
            return self.none()
        return self.filter(empresa=empresa)

    def de_usuario(self, usuario):
        if usuario is None:
            return self.none()
        return self.filter(usuario=usuario)

    def no_leidas(self):
        return self.filter(leida=False)


class Notificacion(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="empresa",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="usuario",
    )
    tipo = models.CharField("tipo", max_length=64, choices=TIPO_CHOICES)
    titulo = models.CharField("título", max_length=200)
    mensaje = models.TextField("mensaje")
    url = models.CharField("url", max_length=500, blank=True)
    leida = models.BooleanField("leída", default=False)
    email_enviado = models.BooleanField("email enviado", default=False)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    objects = NotificacionQuerySet.as_manager()

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["usuario", "leida"], name="notif_usuario_leida_idx"),
            models.Index(
                fields=["empresa", "created_at"],
                name="notif_empresa_created_idx",
            ),
        ]

    def __str__(self):
        return self.titulo
