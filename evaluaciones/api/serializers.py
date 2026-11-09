from decimal import Decimal

from django.db import transaction
from django.db.models import Q
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

    def validate(self, attrs):
        tipo = attrs.get("tipo_item") or PlantillaCriterio.TipoItem.ESCALA
        if tipo == PlantillaCriterio.TipoItem.TEXTO:
            attrs["ponderacion"] = Decimal("0")
            attrs["escala_min"] = attrs.get("escala_min") or 1
            attrs["escala_max"] = attrs.get("escala_max") or 5
            return attrs
        escala_min = attrs.get("escala_min")
        escala_max = attrs.get("escala_max")
        if escala_min is None:
            escala_min = 1
        if escala_max is None:
            escala_max = 5
        if escala_min >= escala_max:
            raise serializers.ValidationError(
                {"escala_max": "La escala mínima debe ser menor que la máxima."}
            )
        ponderacion = attrs.get("ponderacion")
        if ponderacion is not None and ponderacion < 0:
            raise serializers.ValidationError(
                {"ponderacion": "La ponderación no puede ser negativa."}
            )
        return attrs


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
        instancia = self.instance if getattr(self.instance, "pk", None) else None
        puestos = Puesto.objects.filter(empresa=empresa, activo=True)
        competencias = Competencia.objects.filter(empresa=empresa, activa=True)
        if instancia is not None:
            puestos = (
                Puesto.objects.filter(empresa=empresa)
                .filter(Q(activo=True) | Q(pk__in=instancia.puestos.values("pk")))
                .distinct()
            )
            competencias = Competencia.objects.filter(empresa=empresa).filter(
                Q(activa=True) | Q(pk__in=instancia.criterios.values("competencia_id"))
            )
        self.fields["puestos"].child_relation.queryset = puestos.order_by("nombre")
        self.fields["criterios"].child.fields["competencia"].queryset = competencias.order_by(
            "nombre"
        )

    def get_puestos_nombres(self, obj):
        return list(obj.puestos.order_by("nombre").values_list("nombre", flat=True))

    def validate(self, attrs):
        criterios = attrs.get("criterios")
        if self.instance is None and not criterios:
            raise serializers.ValidationError(
                {"criterios": "La plantilla necesita al menos un criterio."}
            )
        if criterios:
            vistos = set()
            for datos in criterios:
                competencia = datos.get("competencia")
                if competencia is None:
                    continue
                pk = getattr(competencia, "pk", competencia)
                if pk in vistos:
                    raise serializers.ValidationError(
                        {"criterios": "No se puede usar la misma competencia más de una vez."}
                    )
                vistos.add(pk)
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
        instancia = self.instance if getattr(self.instance, "pk", None) else None
        plantillas = PlantillaEvaluacion.objects.for_empresa(empresa).filter(activa=True)
        areas = Area.objects.filter(empresa=empresa, activa=True)
        if instancia is not None:
            plantillas = PlantillaEvaluacion.objects.for_empresa(empresa).filter(
                Q(activa=True) | Q(pk=instancia.plantilla_default_id)
            )
            areas = (
                Area.objects.filter(empresa=empresa)
                .filter(Q(activa=True) | Q(pk__in=instancia.areas.values("pk")))
                .distinct()
            )
        self.fields["plantilla_default"].queryset = plantillas.order_by("nombre")
        self.fields["areas"].child_relation.queryset = areas.order_by("nombre")

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio")
        cierre = attrs.get("fecha_cierre")
        if self.instance is not None and getattr(self.instance, "pk", None):
            if inicio is None:
                inicio = self.instance.fecha_inicio
            if cierre is None:
                cierre = self.instance.fecha_cierre
        if inicio and cierre and cierre < inicio:
            raise serializers.ValidationError(
                {"fecha_cierre": "La fecha de cierre no puede ser anterior al inicio."}
            )
        empresa = self.context.get("empresa")
        plantilla = attrs.get("plantilla_default")
        if (
            plantilla is not None
            and empresa is not None
            and plantilla.empresa_id != empresa.pk
        ):
            raise serializers.ValidationError(
                {"plantilla_default": "La plantilla no pertenece a esta empresa."}
            )
        areas = attrs.get("areas") or []
        if empresa is not None and any(area.empresa_id != empresa.pk for area in areas):
            raise serializers.ValidationError(
                {"areas": "No se pueden asociar áreas de otra empresa."}
            )
        return attrs

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

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio")
        cierre = attrs.get("fecha_cierre")
        if inicio and cierre and cierre < inicio:
            raise serializers.ValidationError(
                {"fecha_cierre": "La fecha de cierre no puede ser anterior al inicio."}
            )
        return attrs


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
    estado_display = serializers.CharField(source="etiqueta_estado", read_only=True)
    en_borrador = serializers.BooleanField(read_only=True)
    con_observacion = serializers.BooleanField(read_only=True)
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
            "en_borrador",
            "con_observacion",
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
