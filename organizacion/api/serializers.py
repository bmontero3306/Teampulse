from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from organizacion.models import Area, Competencia, Puesto
from organizacion.services import (
    MENSAJE_SUPERIOR_INACTIVO,
    JerarquiaCircularError,
    validar_desactivacion_puesto,
    validar_jerarquia_areas,
    validar_jerarquia_puestos,
)


class AreaSerializer(serializers.ModelSerializer):
    area_padre_nombre = serializers.CharField(
        source="area_padre.nombre", read_only=True, default=None
    )

    class Meta:
        model = Area
        fields = ("id", "nombre", "area_padre", "area_padre_nombre", "activa")
        extra_kwargs = {"area_padre": {"required": False, "allow_null": True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get("empresa")
        if empresa is None:
            return
        qs = Area.objects.filter(empresa=empresa)
        if self.instance is not None and getattr(self.instance, "pk", None):
            qs = qs.exclude(pk=self.instance.pk)
        self.fields["area_padre"].queryset = qs

    def validate(self, attrs):
        empresa = self.context["empresa"]
        padre = attrs.get("area_padre", getattr(self.instance, "area_padre", None))
        if padre is not None and padre.empresa_id != empresa.pk:
            raise serializers.ValidationError(
                {"area_padre": "El área padre debe pertenecer a la misma empresa."}
            )
        instancia = self.instance if self.instance is not None else Area(empresa=empresa)
        try:
            validar_jerarquia_areas(instancia, padre)
        except JerarquiaCircularError as exc:
            raise serializers.ValidationError({"area_padre": str(exc)}) from exc
        return attrs

    def create(self, validated_data):
        area = Area(empresa=self.context["empresa"], **validated_data)
        area.full_clean()
        area.save()
        return area

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        return instance


class PuestoSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default=None)
    puesto_superior_nombre = serializers.CharField(
        source="puesto_superior.nombre", read_only=True, default=None
    )

    class Meta:
        model = Puesto
        fields = (
            "id",
            "nombre",
            "descripcion",
            "area",
            "area_nombre",
            "puesto_superior",
            "puesto_superior_nombre",
            "activo",
        )
        extra_kwargs = {
            "descripcion": {"required": False, "allow_blank": True},
            "area": {"required": False, "allow_null": True},
            "puesto_superior": {"required": False, "allow_null": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get("empresa")
        if empresa is None:
            return
        self.fields["area"].queryset = Area.objects.filter(empresa=empresa)
        superiores = Puesto.objects.filter(empresa=empresa)
        if self.instance is not None and getattr(self.instance, "pk", None):
            superiores = superiores.exclude(pk=self.instance.pk)
        self.fields["puesto_superior"].queryset = superiores

    def validate(self, attrs):
        empresa = self.context["empresa"]
        area = attrs.get("area", getattr(self.instance, "area", None))
        superior = attrs.get(
            "puesto_superior", getattr(self.instance, "puesto_superior", None)
        )
        if area is not None and area.empresa_id != empresa.pk:
            raise serializers.ValidationError(
                {"area": "El área debe pertenecer a la misma empresa."}
            )
        if superior is not None and superior.empresa_id != empresa.pk:
            raise serializers.ValidationError(
                {
                    "puesto_superior": "El puesto superior debe pertenecer a la misma empresa."
                }
            )
        instancia = self.instance if self.instance is not None else Puesto(empresa=empresa)
        try:
            validar_jerarquia_puestos(instancia, superior)
        except JerarquiaCircularError as exc:
            raise serializers.ValidationError({"puesto_superior": str(exc)}) from exc
        activo = attrs.get("activo", getattr(self.instance, "activo", True))
        if (
            self.instance is not None
            and getattr(self.instance, "pk", None)
            and self.instance.activo
            and not activo
        ):
            try:
                validar_desactivacion_puesto(self.instance)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict) from exc
        if activo and superior is not None and not superior.activo:
            raise serializers.ValidationError(
                {"puesto_superior": MENSAJE_SUPERIOR_INACTIVO}
            )
        return attrs

    def create(self, validated_data):
        puesto = Puesto(empresa=self.context["empresa"], **validated_data)
        puesto.full_clean()
        puesto.save()
        return puesto

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        return instance


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = ("id", "nombre", "descripcion", "tipo", "activa")
        extra_kwargs = {"descripcion": {"required": False, "allow_blank": True}}

    def create(self, validated_data):
        competencia = Competencia(empresa=self.context["empresa"], **validated_data)
        competencia.full_clean()
        competencia.save()
        return competencia

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        return instance
