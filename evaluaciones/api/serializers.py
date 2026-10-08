from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from cuentas.api.serializers import UsuarioBreveSerializer
from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaCriterio,
    PlantillaEvaluacion,
    PlantillaPuesto,
    RespuestaItem,
)
from organizacion.models import Area, Competencia, Puesto


class CriterioSerializer(serializers.ModelSerializer):
    competencia_nombre = serializers.CharField(source="competencia.nombre", read_only=True)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = PlantillaCriterio
        fields = (
            "id",
            "competencia",
            "competencia_nombre",
            "categoria",
            "tipo_item",
            "orden",
            "escala_min",
            "escala_max",
            "ponderacion",
            "comentario_empleado_obligatorio",
            "comentario_supervisor_obligatorio",
        )
        extra_kwargs = {
            "categoria": {"required": False, "allow_blank": True},
            "competencia": {"required": True},
        }


class PlantillaSerializer(serializers.ModelSerializer):
    criterios = CriterioSerializer(many=True)
    puestos = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Puesto.objects.none(), required=False
    )
    puestos_nombres = serializers.SerializerMethodField()

    class Meta:
        model = PlantillaEvaluacion
        fields = (
            "id",
            "nombre",
            "tipo",
            "descripcion",
            "activa",
            "puestos",
            "puestos_nombres",
            "criterios",
            "duplicada_desde",
        )
        read_only_fields = ("duplicada_desde",)
        extra_kwargs = {"descripcion": {"required": False, "allow_blank": True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get("empresa")
        if empresa is None:
            return
        self.fields["puestos"].child_relation.queryset = Puesto.objects.filter(empresa=empresa)
        self.fields["criterios"].child.fields["competencia"].queryset = Competencia.objects.filter(
            empresa=empresa
        )

    def get_puestos_nombres(self, obj):
        return list(obj.puestos.order_by("nombre").values_list("nombre", flat=True))

    def validate(self, attrs):
        criterios = attrs.get("criterios")
        if self.instance is None and not criterios:
            raise serializers.ValidationError(
                {"criterios": "La plantilla necesita al menos un criterio."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        criterios = validated_data.pop("criterios", [])
        puestos = validated_data.pop("puestos", [])
        plantilla = PlantillaEvaluacion(empresa=self.context["empresa"], **validated_data)
        plantilla.full_clean()
        plantilla.save()
        self._guardar_criterios(plantilla, criterios)
        self._guardar_puestos(plantilla, puestos)
        return plantilla

    @transaction.atomic
    def update(self, instance, validated_data):
        criterios = validated_data.pop("criterios", None)
        puestos = validated_data.pop("puestos", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        if criterios is not None:
            self._guardar_criterios(instance, criterios, reemplazar=True)
        if puestos is not None:
            self._guardar_puestos(instance, puestos, reemplazar=True)
        return instance

    def _guardar_puestos(self, plantilla, puestos, reemplazar=False):
        if reemplazar:
            plantilla.plantilla_puestos.all().delete()
        for puesto in puestos:
            vinculo = PlantillaPuesto(plantilla=plantilla, puesto=puesto)
            vinculo.full_clean()
            vinculo.save()

    def _guardar_criterios(self, plantilla, criterios, reemplazar=False):
        existentes = {c.pk: c for c in plantilla.criterios.all()} if reemplazar else {}
        vistos = set()
        for datos in criterios:
            pk = datos.pop("id", None)
            criterio = existentes.get(pk) if pk else None
            if criterio is None:
                criterio = PlantillaCriterio(plantilla=plantilla)
            for campo, valor in datos.items():
                setattr(criterio, campo, valor)
            if criterio.es_texto:
                criterio.ponderacion = Decimal("0")
            criterio.full_clean()
            criterio.save()
            vistos.add(criterio.pk)
        if reemplazar:
            for pk, criterio in existentes.items():
                if pk not in vistos:
                    criterio.delete()


class CicloSerializer(serializers.ModelSerializer):
    plantilla_nombre = serializers.CharField(source="plantilla_default.nombre", read_only=True)
    total_evals = serializers.IntegerField(read_only=True)
    sin_evaluador_count = serializers.IntegerField(read_only=True)
    areas = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Area.objects.none(), required=False
    )

    class Meta:
        model = CicloEvaluacion
        fields = (
            "id",
            "nombre",
            "fecha_inicio",
            "fecha_cierre",
            "estado",
            "plantilla_default",
            "plantilla_nombre",
            "areas",
            "criterios_generales",
            "activado_en",
            "total_evals",
            "sin_evaluador_count",
        )
        read_only_fields = ("estado", "activado_en")
        extra_kwargs = {"criterios_generales": {"required": False, "allow_blank": True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get("empresa")
        if empresa is None:
            return
        self.fields["plantilla_default"].queryset = PlantillaEvaluacion.objects.for_empresa(empresa)
        self.fields["areas"].child_relation.queryset = Area.objects.filter(empresa=empresa)

    def create(self, validated_data):
        areas = validated_data.pop("areas", [])
        ciclo = CicloEvaluacion(
            empresa=self.context["empresa"],
            estado=CicloEvaluacion.Estado.BORRADOR,
            **validated_data,
        )
        ciclo.full_clean()
        ciclo.save()
        if areas:
            ciclo.areas.set(areas)
        return ciclo

    def update(self, instance, validated_data):
        if instance.estado != CicloEvaluacion.Estado.BORRADOR:
            raise serializers.ValidationError(
                "Solo se puede editar un ciclo en borrador. Usá reprogramar para las fechas."
            )
        areas = validated_data.pop("areas", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        if areas is not None:
            instance.areas.set(areas)
        return instance


class ReprogramarSerializer(serializers.Serializer):
    fecha_inicio = serializers.DateField()
    fecha_cierre = serializers.DateField()


class RespuestaSerializer(serializers.ModelSerializer):
    competencia = serializers.CharField(source="criterio.competencia.nombre", read_only=True)
    categoria = serializers.CharField(source="criterio.categoria", read_only=True)
    tipo_item = serializers.CharField(source="criterio.tipo_item", read_only=True)
    orden = serializers.IntegerField(source="criterio.orden", read_only=True)
    escala_min = serializers.IntegerField(source="criterio.escala_min", read_only=True)
    escala_max = serializers.IntegerField(source="criterio.escala_max", read_only=True)
    ponderacion = serializers.DecimalField(
        source="criterio.ponderacion", max_digits=5, decimal_places=2, read_only=True
    )
    comentario_empleado_obligatorio = serializers.BooleanField(
        source="criterio.comentario_empleado_obligatorio", read_only=True
    )
    comentario_supervisor_obligatorio = serializers.BooleanField(
        source="criterio.comentario_supervisor_obligatorio", read_only=True
    )
    brecha = serializers.IntegerField(read_only=True)

    class Meta:
        model = RespuestaItem
        fields = (
            "id",
            "competencia",
            "categoria",
            "tipo_item",
            "orden",
            "escala_min",
            "escala_max",
            "ponderacion",
            "comentario_empleado_obligatorio",
            "comentario_supervisor_obligatorio",
            "puntaje_empleado",
            "comentario_empleado",
            "puntaje_supervisor",
            "comentario_supervisor",
            "brecha",
        )


class EvaluacionListaSerializer(serializers.ModelSerializer):
    ciclo_nombre = serializers.CharField(source="ciclo.nombre", read_only=True)
    evaluado = UsuarioBreveSerializer(read_only=True)
    evaluador = UsuarioBreveSerializer(read_only=True)
    puesto_nombre = serializers.CharField(source="puesto.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    esta_cerrada = serializers.BooleanField(read_only=True)
    comparacion_revelada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Evaluacion
        fields = (
            "id",
            "ciclo",
            "ciclo_nombre",
            "estado",
            "estado_display",
            "evaluado",
            "evaluador",
            "puesto",
            "puesto_nombre",
            "sin_evaluador",
            "esta_cerrada",
            "comparacion_revelada",
            "plantilla",
        )


class EvaluacionDetalleSerializer(EvaluacionListaSerializer):
    respuestas = RespuestaSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    plantilla_nombre = serializers.CharField(source="plantilla.nombre", read_only=True)

    class Meta(EvaluacionListaSerializer.Meta):
        fields = EvaluacionListaSerializer.Meta.fields + (
            "empresa_nombre",
            "plantilla_nombre",
            "feedback_supervisor",
            "reunion_fecha",
            "reunion_notas",
            "comentario_empleado_cierre",
            "enviada_auto_en",
            "cerrada_supervisor_en",
            "firmada_en",
            "firma_hash",
            "respuestas",
        )


class RespuestaInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    puntaje_empleado = serializers.IntegerField(required=False, allow_null=True)
    comentario_empleado = serializers.CharField(required=False, allow_blank=True)
    puntaje_supervisor = serializers.IntegerField(required=False, allow_null=True)
    comentario_supervisor = serializers.CharField(required=False, allow_blank=True)


class AutoevaluacionInputSerializer(serializers.Serializer):
    enviar = serializers.BooleanField(default=False)
    respuestas = RespuestaInputSerializer(many=True)


class SupervisarInputSerializer(serializers.Serializer):
    cerrar = serializers.BooleanField(default=False)
    habilitar_reunion = serializers.BooleanField(default=False)
    feedback_supervisor = serializers.CharField(required=False, allow_blank=True)
    respuestas = RespuestaInputSerializer(many=True)


class FirmarInputSerializer(serializers.Serializer):
    observacion = serializers.CharField(required=False, allow_blank=True)


class ReunionInputSerializer(serializers.Serializer):
    reunion_fecha = serializers.DateTimeField()
    reunion_notas = serializers.CharField()


class ReasignarInputSerializer(serializers.Serializer):
    evaluador = serializers.IntegerField()
