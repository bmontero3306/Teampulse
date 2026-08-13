from django.db import models

from empresas.validators import normalizar_cuit, validar_cuit


class Empresa(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        SUSPENDIDA = "suspendida", "Suspendida"
        INACTIVA = "inactiva", "Inactiva"

    nombre = models.CharField("nombre", max_length=200)
    razon_social = models.CharField("razón social", max_length=200)
    cuit = models.CharField("CUIT", max_length=20, unique=True)
    email_contacto = models.EmailField("email de contacto")
    telefono = models.CharField("teléfono", max_length=50, blank=True)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )
    parametros = models.JSONField("parámetros", default=dict, blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.cuit:
            self.cuit = validar_cuit(self.cuit)

    def save(self, *args, **kwargs):
        if self.cuit:
            self.cuit = normalizar_cuit(self.cuit)
        super().save(*args, **kwargs)

    @property
    def permite_login(self):
        """Los usuarios de la empresa solo autenticán si está activa (chequeo en WP2)."""
        return self.estado == self.Estado.ACTIVA
