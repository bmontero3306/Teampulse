from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app.querysets import EmpresaQuerySet


class PlantillaEvaluacion(models.Model):
    class Tipo(models.TextChoices):
        TECNICA = "tecnica", "Técnica"
        ACTITUDINAL = "actitudinal", "Actitudinal"
        OBJETIVOS = "objetivos", "Objetivos"
        MIXTA = "mixta", "Mixta"

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="plantillas",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=200)
    tipo = models.CharField(
        "tipo",
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.MIXTA,
    )
    descripcion = models.TextField("descripción", blank=True)
    activa = models.BooleanField("activa", default=True)
    duplicada_desde = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicadas",
        verbose_name="duplicada desde",
    )
    puestos = models.ManyToManyField(
        "organizacion.Puesto",
        through="PlantillaPuesto",
        related_name="plantillas",
        blank=True,
        verbose_name="puestos",
    )

    objects = models.Manager.from_queryset(EmpresaQuerySet)()

    class Meta:
        verbose_name = "plantilla de evaluación"
        verbose_name_plural = "plantillas de evaluación"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class PlantillaCriterio(models.Model):
    class TipoItem(models.TextChoices):
        ESCALA = "escala", "Escala numérica"
        TEXTO = "texto", "Solo texto"

    plantilla = models.ForeignKey(
        PlantillaEvaluacion,
        on_delete=models.CASCADE,
        related_name="criterios",
        verbose_name="plantilla",
    )
    competencia = models.ForeignKey(
        "organizacion.Competencia",
        on_delete=models.PROTECT,
        related_name="criterios_plantilla",
        verbose_name="competencia",
    )
    categoria = models.CharField("categoría", max_length=200, blank=True)
    tipo_item = models.CharField(
        "tipo de ítem",
        max_length=20,
        choices=TipoItem.choices,
        default=TipoItem.ESCALA,
    )
    orden = models.PositiveIntegerField("orden", default=1)
    escala_min = models.IntegerField("escala mínima", default=1)
    escala_max = models.IntegerField("escala máxima", default=5)
    ponderacion = models.DecimalField(
        "ponderación",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    comentario_empleado_obligatorio = models.BooleanField(
        "comentario del empleado obligatorio",
        default=True,
    )
    comentario_supervisor_obligatorio = models.BooleanField(
        "comentario del supervisor obligatorio",
        default=True,
    )

    class Meta:
        verbose_name = "criterio de plantilla"
        verbose_name_plural = "criterios de plantilla"
        ordering = ["orden", "pk"]

    def __str__(self):
        return f"{self.plantilla} · {self.competencia}"

    @property
    def es_escala(self):
        return self.tipo_item == self.TipoItem.ESCALA

    @property
    def es_texto(self):
        return self.tipo_item == self.TipoItem.TEXTO

    def clean(self):
        super().clean()
        if self.es_texto:
            self.ponderacion = Decimal("0")
        else:
            if (
                self.escala_min is not None
                and self.escala_max is not None
                and self.escala_min >= self.escala_max
            ):
                raise ValidationError(
                    {
                        "escala_max": "La escala mínima debe ser menor que la máxima.",
                    }
                )
        if self.ponderacion is not None and self.ponderacion < 0:
            raise ValidationError(
                {"ponderacion": "La ponderación no puede ser negativa."}
            )
        plantilla = getattr(self, "plantilla", None)
        competencia = getattr(self, "competencia", None)
        if not plantilla or not competencia:
            return
        empresa_plantilla = getattr(plantilla, "empresa_id", None)
        empresa_comp = getattr(competencia, "empresa_id", None)
        if empresa_plantilla and empresa_comp and empresa_plantilla != empresa_comp:
            raise ValidationError(
                {
                    "competencia": "La competencia debe pertenecer a la misma empresa que la plantilla."
                }
            )


class PlantillaPuesto(models.Model):
    plantilla = models.ForeignKey(
        PlantillaEvaluacion,
        on_delete=models.CASCADE,
        related_name="plantilla_puestos",
        verbose_name="plantilla",
    )
    puesto = models.ForeignKey(
        "organizacion.Puesto",
        on_delete=models.CASCADE,
        related_name="plantilla_puestos",
        verbose_name="puesto",
    )

    class Meta:
        verbose_name = "puesto de plantilla"
        verbose_name_plural = "puestos de plantilla"
        constraints = [
            models.UniqueConstraint(
                fields=["plantilla", "puesto"],
                name="uniq_plantilla_puesto",
            ),
        ]

    def __str__(self):
        return f"{self.plantilla} · {self.puesto}"

    def clean(self):
        super().clean()
        plantilla = getattr(self, "plantilla", None)
        puesto = getattr(self, "puesto", None)
        if not plantilla or not puesto:
            return
        empresa_plantilla = getattr(plantilla, "empresa_id", None)
        empresa_puesto = getattr(puesto, "empresa_id", None)
        if empresa_plantilla and empresa_puesto and empresa_plantilla != empresa_puesto:
            raise ValidationError(
                {
                    "puesto": "El puesto debe pertenecer a la misma empresa que la plantilla."
                }
            )


class CicloEvaluacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ACTIVO = "activo", "Activo"
        PAUSADO = "pausado", "Pausado"
        CERRADO = "cerrado", "Cerrado"
        CANCELADO = "cancelado", "Cancelado"

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="ciclos",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=200)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_cierre = models.DateField("fecha de cierre")
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )
    plantilla_default = models.ForeignKey(
        PlantillaEvaluacion,
        on_delete=models.PROTECT,
        related_name="ciclos_default",
        verbose_name="plantilla por defecto",
    )
    areas = models.ManyToManyField(
        "organizacion.Area",
        related_name="ciclos",
        blank=True,
        verbose_name="áreas",
    )
    criterios_generales = models.TextField("criterios generales", blank=True)
    activado_en = models.DateTimeField("activado en", null=True, blank=True)
    activado_por = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ciclos_activados",
        verbose_name="activado por",
    )

    objects = models.Manager.from_queryset(EmpresaQuerySet)()

    class Meta:
        verbose_name = "ciclo de evaluación"
        verbose_name_plural = "ciclos de evaluación"
        ordering = ["-fecha_inicio", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa"],
                condition=models.Q(estado="activo"),
                name="uniq_ciclo_activo_por_empresa",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_cierre and self.fecha_cierre < self.fecha_inicio:
            raise ValidationError(
                {"fecha_cierre": "La fecha de cierre no puede ser anterior al inicio."}
            )
        plantilla = getattr(self, "plantilla_default", None)
        if (
            plantilla
            and getattr(plantilla, "empresa_id", None)
            and self.empresa_id
            and plantilla.empresa_id != self.empresa_id
        ):
            raise ValidationError(
                {
                    "plantilla_default": "La plantilla debe pertenecer a la misma empresa que el ciclo."
                }
            )


class Evaluacion(models.Model):
    class Estado(models.TextChoices):
        AUTOEVALUACION = "autoevaluacion", "Autoevaluación"
        SUPERVISOR = "evaluacion_supervisor", "Evaluación del supervisor"
        PENDIENTE_REUNION = "pendiente_reunion", "Pendiente de reunión"
        PENDIENTE_CONFORMIDAD = "pendiente_conformidad", "Pendiente de conformidad"
        CERRADA = "cerrada", "Cerrada"

    ciclo = models.ForeignKey(
        CicloEvaluacion,
        on_delete=models.PROTECT,
        related_name="evaluaciones",
        verbose_name="ciclo",
    )
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="evaluaciones",
        verbose_name="empresa",
    )
    evaluado = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        related_name="evaluaciones_recibidas",
        verbose_name="evaluado",
    )
    evaluador = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evaluaciones_a_cargo",
        verbose_name="evaluador",
    )
    puesto = models.ForeignKey(
        "organizacion.Puesto",
        on_delete=models.PROTECT,
        related_name="evaluaciones_snapshot",
        verbose_name="puesto",
    )
    plantilla = models.ForeignKey(
        PlantillaEvaluacion,
        on_delete=models.PROTECT,
        related_name="evaluaciones",
        verbose_name="plantilla",
    )
    estado = models.CharField(
        "estado",
        max_length=30,
        choices=Estado.choices,
        default=Estado.AUTOEVALUACION,
    )
    sin_evaluador = models.BooleanField("sin evaluador", default=False)
    comentario_empleado_cierre = models.TextField(
        "comentario del empleado al cierre",
        blank=True,
    )
    feedback_supervisor = models.TextField("feedback del supervisor", blank=True)
    reunion_fecha = models.DateTimeField("fecha de reunión de feedback", null=True, blank=True)
    reunion_notas = models.TextField("notas de la reunión de feedback", blank=True)
    reunion_registrada_en = models.DateTimeField(
        "reunión registrada en",
        null=True,
        blank=True,
    )
    reunion_registrada_por = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reuniones_feedback_registradas",
        verbose_name="reunión registrada por",
    )
    enviada_auto_en = models.DateTimeField("enviada autoevaluación en", null=True, blank=True)
    cerrada_supervisor_en = models.DateTimeField(
        "cerrada por supervisor en",
        null=True,
        blank=True,
    )
    firmada_en = models.DateTimeField("firmada en", null=True, blank=True)
    firma_hash = models.CharField("hash de firma", max_length=64, blank=True)
    ip_firma = models.GenericIPAddressField("IP de firma", null=True, blank=True)

    objects = models.Manager.from_queryset(EmpresaQuerySet)()

    class Meta:
        verbose_name = "evaluación"
        verbose_name_plural = "evaluaciones"
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["ciclo", "evaluado"],
                name="uniq_evaluacion_ciclo_evaluado",
            ),
        ]

    def __str__(self):
        return f"{self.evaluado} · {self.ciclo}"

    @property
    def esta_cerrada(self):
        return self.estado == self.Estado.CERRADA

    @property
    def comparacion_revelada(self):
        return self.estado in (
            self.Estado.PENDIENTE_REUNION,
            self.Estado.PENDIENTE_CONFORMIDAD,
            self.Estado.CERRADA,
        )

    def _respuestas_cacheadas(self):
        cache = getattr(self, "_prefetched_objects_cache", None) or {}
        if "respuestas" in cache:
            return cache["respuestas"]
        return None

    @property
    def en_borrador(self):
        """Hay contenido guardado y la fase todavía no se envió o cerró."""
        if self.estado == self.Estado.AUTOEVALUACION:
            respuestas = self._respuestas_cacheadas()
            if respuestas is None:
                return self.respuestas.filter(
                    models.Q(puntaje_empleado__isnull=False)
                    | ~models.Q(comentario_empleado="")
                ).exists()
            return any(
                item.puntaje_empleado is not None
                or (item.comentario_empleado or "").strip()
                for item in respuestas
            )
        if self.estado == self.Estado.SUPERVISOR:
            if (self.feedback_supervisor or "").strip():
                return True
            respuestas = self._respuestas_cacheadas()
            if respuestas is None:
                return self.respuestas.filter(
                    models.Q(puntaje_supervisor__isnull=False)
                    | ~models.Q(comentario_supervisor="")
                ).exists()
            return any(
                item.puntaje_supervisor is not None
                or (item.comentario_supervisor or "").strip()
                for item in respuestas
            )
        return False

    @property
    def con_observacion(self):
        return self.esta_cerrada and bool((self.comentario_empleado_cierre or "").strip())

    @property
    def etiqueta_estado(self):
        if self.estado == self.Estado.AUTOEVALUACION:
            if self.en_borrador:
                return "Autoevaluación en borrador"
            return "Autoevaluación"
        if self.estado == self.Estado.SUPERVISOR:
            if self.en_borrador:
                return "Evaluación del supervisor en borrador"
            return "Evaluación del supervisor"
        if self.con_observacion:
            return "Cerrada con observación"
        return self.get_estado_display()


class RespuestaItem(models.Model):
    evaluacion = models.ForeignKey(
        Evaluacion,
        on_delete=models.CASCADE,
        related_name="respuestas",
        verbose_name="evaluación",
    )
    criterio = models.ForeignKey(
        PlantillaCriterio,
        on_delete=models.PROTECT,
        related_name="respuestas",
        verbose_name="criterio",
    )
    puntaje_empleado = models.IntegerField("puntaje del empleado", null=True, blank=True)
    comentario_empleado = models.TextField("comentario del empleado", blank=True)
    puntaje_supervisor = models.IntegerField(
        "puntaje del supervisor",
        null=True,
        blank=True,
    )
    comentario_supervisor = models.TextField("comentario del supervisor", blank=True)

    class Meta:
        verbose_name = "ítem de respuesta"
        verbose_name_plural = "ítems de respuesta"
        ordering = ["criterio__orden", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["evaluacion", "criterio"],
                name="uniq_respuesta_evaluacion_criterio",
            ),
        ]

    def __str__(self):
        return f"{self.evaluacion} · {self.criterio}"

    @property
    def brecha(self):
        if self.puntaje_empleado is None or self.puntaje_supervisor is None:
            return None
        return self.puntaje_supervisor - self.puntaje_empleado

    @property
    def brecha_display(self):
        if self.brecha is None:
            return "—"
        if self.brecha > 0:
            return f"+{self.brecha}"
        return str(self.brecha)
