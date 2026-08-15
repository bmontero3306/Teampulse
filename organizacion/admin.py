from django.contrib import admin

from organizacion.models import Area, Competencia, Puesto


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "area_padre", "activa")
    list_filter = ("empresa", "activa")
    search_fields = ("nombre",)


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "area", "puesto_superior", "activo")
    list_filter = ("empresa", "activo", "area")
    search_fields = ("nombre",)


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "tipo", "activa")
    list_filter = ("empresa", "tipo", "activa")
    search_fields = ("nombre",)
