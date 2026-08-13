from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from app.querysets import EmpresaQuerySet


class AreaQuerySet(EmpresaQuerySet):
    def delete(self):
        n = self.update(activa=False)
        return n, {self.model._meta.label: n}


class PuestoQuerySet(EmpresaQuerySet):
    def delete(self):
        n = self.update(activo=False)
        return n, {self.model._meta.label: n}


class CompetenciaQuerySet(EmpresaQuerySet):
    def delete(self):
        n = self.update(activa=False)
        return n, {self.model._meta.label: n}


class Area(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="areas",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=200)
    area_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="areas_hijas",
        verbose_name="área padre",
    )
    activa = models.BooleanField("activa", default=True)

    objects = models.Manager.from_queryset(AreaQuerySet)()

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.area_padre_id:
            if self.pk and self.area_padre_id == self.pk:
                raise ValidationError(
                    {"area_padre": "Un área no puede ser padre de sí misma."}
                )
            if (
                self.empresa_id
                and self.area_padre.empresa_id
                and self.area_padre.empresa_id != self.empresa_id
            ):
                raise ValidationError(
                    {"area_padre": "El área padre debe pertenecer a la misma empresa."}
                )
            from organizacion.services import (
                JerarquiaCircularError,
                validar_jerarquia_areas,
            )

            try:
                validar_jerarquia_areas(self, self.area_padre)
            except JerarquiaCircularError as exc:
                raise ValidationError({"area_padre": str(exc)}) from exc

    def delete(self, using=None, keep_parents=False):
        self.activa = False
        self.save(update_fields=["activa"])


class Puesto(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="puestos",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    area = models.ForeignKey(
        "organizacion.Area",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puestos",
        verbose_name="área",
    )
    puesto_superior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puestos_hijos",
        verbose_name="puesto superior",
    )
    activo = models.BooleanField("activo", default=True)

    objects = models.Manager.from_queryset(PuestoQuerySet)()

    class Meta:
        verbose_name = "puesto"
        verbose_name_plural = "puestos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.area_id and self.empresa_id and self.area.empresa_id != self.empresa_id:
            raise ValidationError(
                {"area": "El área debe pertenecer a la misma empresa."}
            )
        if self.puesto_superior_id:
            if self.pk and self.puesto_superior_id == self.pk:
                raise ValidationError(
                    {"puesto_superior": "Un puesto no puede ser superior de sí mismo."}
                )
            if (
                self.empresa_id
                and self.puesto_superior.empresa_id
                and self.puesto_superior.empresa_id != self.empresa_id
            ):
                raise ValidationError(
                    {
                        "puesto_superior": "El puesto superior debe pertenecer a la misma empresa."
                    }
                )
            from organizacion.services import (
                JerarquiaCircularError,
                validar_jerarquia_puestos,
            )

            try:
                validar_jerarquia_puestos(self, self.puesto_superior)
            except JerarquiaCircularError as exc:
                raise ValidationError({"puesto_superior": str(exc)}) from exc

    def delete(self, using=None, keep_parents=False):
        self.activo = False
        self.save(update_fields=["activo"])


class Competencia(models.Model):
    class Tipo(models.TextChoices):
        TECNICA = "tecnica", "Técnica"
        ACTITUDINAL = "actitudinal", "Actitudinal"
        OBJETIVO = "objetivo", "Objetivo"
        OTRA = "otra", "Otra"

    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="competencias",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    tipo = models.CharField(
        "tipo",
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.TECNICA,
    )
    activa = models.BooleanField("activa", default=True)

    objects = models.Manager.from_queryset(CompetenciaQuerySet)()

    class Meta:
        verbose_name = "competencia"
        verbose_name_plural = "competencias"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def delete(self, using=None, keep_parents=False):
        self.activa = False
        self.save(update_fields=["activa"])


class PuestoCompetencia(models.Model):
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.CASCADE,
        related_name="puesto_competencias",
        verbose_name="puesto",
    )
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name="puesto_competencias",
        verbose_name="competencia",
    )
    ponderacion = models.DecimalField(
        "ponderación",
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )

    class Meta:
        verbose_name = "competencia de puesto"
        verbose_name_plural = "competencias de puesto"
        constraints = [
            models.UniqueConstraint(
                fields=["puesto", "competencia"],
                name="uniq_puesto_competencia",
            ),
        ]

    def __str__(self):
        return f"{self.puesto} · {self.competencia}"

    def clean(self):
        super().clean()
        puesto = getattr(self, "puesto", None)
        competencia = getattr(self, "competencia", None)
        if not puesto or not competencia:
            return
        empresa_puesto = getattr(puesto, "empresa_id", None)
        empresa_comp = getattr(competencia, "empresa_id", None)
        if empresa_puesto and empresa_comp and empresa_puesto != empresa_comp:
            raise ValidationError(
                {
                    "competencia": "La competencia debe pertenecer a la misma empresa que el puesto."
                }
            )
