from django.contrib import admin

from notificaciones.models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "usuario",
        "empresa",
        "tipo",
        "leida",
        "email_enviado",
        "created_at",
    )
    list_filter = ("empresa", "tipo", "leida", "email_enviado")
    search_fields = ("titulo", "mensaje", "usuario__email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
