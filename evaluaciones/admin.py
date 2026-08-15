from django.contrib import admin

from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaCriterio,
    PlantillaEvaluacion,
    PlantillaPuesto,
    RespuestaItem,
)


class PlantillaCriterioInline(admin.TabularInline):
    model = PlantillaCriterio
    extra = 1


class PlantillaPuestoInline(admin.TabularInline):
    model = PlantillaPuesto
    extra = 1


@admin.register(PlantillaEvaluacion)
class PlantillaEvaluacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "tipo", "activa")
    list_filter = ("empresa", "tipo", "activa")
    search_fields = ("nombre",)
    inlines = [PlantillaCriterioInline, PlantillaPuestoInline]


@admin.register(PlantillaCriterio)
class PlantillaCriterioAdmin(admin.ModelAdmin):
    list_display = (
        "plantilla",
        "competencia",
        "orden",
        "escala_min",
        "escala_max",
        "ponderacion",
    )
    list_filter = ("plantilla__empresa", "competencia__tipo")
    search_fields = ("plantilla__nombre", "competencia__nombre")


@admin.register(PlantillaPuesto)
class PlantillaPuestoAdmin(admin.ModelAdmin):
    list_display = ("plantilla", "puesto")
    list_filter = ("plantilla__empresa",)
    search_fields = ("plantilla__nombre", "puesto__nombre")


class RespuestaItemInline(admin.TabularInline):
    model = RespuestaItem
    extra = 0


@admin.register(CicloEvaluacion)
class CicloEvaluacionAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "empresa",
        "estado",
        "fecha_inicio",
        "fecha_cierre",
        "plantilla_default",
    )
    list_filter = ("empresa", "estado")
    search_fields = ("nombre",)
    filter_horizontal = ("areas",)
    readonly_fields = ("activado_en", "activado_por")


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = (
        "evaluado",
        "ciclo",
        "empresa",
        "estado",
        "evaluador",
        "sin_evaluador",
    )
    list_filter = ("empresa", "estado", "sin_evaluador")
    search_fields = ("evaluado__email", "evaluador__email", "ciclo__nombre")
    readonly_fields = (
        "firma_hash",
        "firmada_en",
        "ip_firma",
        "enviada_auto_en",
        "cerrada_supervisor_en",
        "reunion_registrada_en",
        "reunion_registrada_por",
    )
    inlines = [RespuestaItemInline]


@admin.register(RespuestaItem)
class RespuestaItemAdmin(admin.ModelAdmin):
    list_display = (
        "evaluacion",
        "criterio",
        "puntaje_empleado",
        "puntaje_supervisor",
    )
    list_filter = ("evaluacion__empresa",)
    search_fields = (
        "evaluacion__evaluado__email",
        "criterio__competencia__nombre",
    )
