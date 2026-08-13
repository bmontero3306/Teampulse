from django.contrib import admin

from empresas.models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cuit", "estado", "email_contacto", "created_at")
    list_filter = ("estado",)
    search_fields = ("nombre", "cuit", "razon_social", "email_contacto")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("nombre",)

    def has_delete_permission(self, request, obj=None):
        return False
