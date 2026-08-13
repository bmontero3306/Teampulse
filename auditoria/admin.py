from django.contrib import admin

from auditoria.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "empresa",
        "usuario",
        "accion",
        "modelo",
        "object_id",
        "ip",
    )
    list_filter = ("empresa", "accion", "modelo", "created_at")
    search_fields = ("accion", "modelo", "object_id", "usuario__email")
    readonly_fields = (
        "empresa",
        "usuario",
        "accion",
        "modelo",
        "object_id",
        "payload",
        "ip",
        "user_agent",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
