from rest_framework import serializers

from organizacion.models import Area, Competencia, Puesto


class AreaSerializer(serializers.ModelSerializer):
    area_padre_nombre = serializers.CharField(
        source="area_padre.nombre", read_only=True, default=None
    )

    class Meta:
        model = Area
        fields = ("id", "nombre", "area_padre", "area_padre_nombre", "activa")
        extra_kwargs = {"area_padre": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        empresa = self.context["empresa"]
        padre = attrs.get("area_padre", getattr(self.instance, "area_padre", None))
        if padre is not None and padre.empresa_id != empresa.pk:
            raise serializers.ValidationError(
                {"area_padre": "El área padre debe pertenecer a la misma empresa."}
            )
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
        self.fields["puesto_superior"].queryset = Puesto.objects.filter(empresa=empresa)

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
