from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from cuentas.models import ROLES_GESTION, Usuario
from cuentas.services import sincronizar_supervisor
from empresas.models import Empresa
from organizacion.models import Area, Puesto


class EmpresaBreveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ("id", "nombre", "estado")


class UsuarioBreveSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "email", "nombre", "first_name", "last_name", "rol", "rol_display")

    def get_nombre(self, obj):
        return obj.get_full_name() or obj.email


class UsuarioSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True, default=None)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default=None)
    puesto_nombre = serializers.CharField(source="puesto.nombre", read_only=True, default=None)
    supervisor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "nombre",
            "rol",
            "rol_display",
            "empresa",
            "empresa_nombre",
            "dni",
            "puesto",
            "puesto_nombre",
            "area",
            "area_nombre",
            "supervisor",
            "supervisor_nombre",
            "is_active",
            "bloqueado",
            "must_change_password",
        )
        read_only_fields = ("empresa", "must_change_password")

    def get_nombre(self, obj):
        return obj.get_full_name() or obj.email

    def get_supervisor_nombre(self, obj):
        if obj.supervisor_id is None:
            return None
        return obj.supervisor.get_full_name() or obj.supervisor.email


class UsuarioWriteSerializer(serializers.ModelSerializer):
    rol = serializers.ChoiceField(choices=ROLES_GESTION)
    clave_temporal = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "dni",
            "rol",
            "area",
            "puesto",
            "supervisor",
            "is_active",
            "bloqueado",
            "clave_temporal",
        )
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "email": {"required": True},
            "is_active": {"required": False},
            "bloqueado": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa = self.context.get("empresa")
        if self.instance is None:
            self.fields.pop("is_active", None)
            self.fields.pop("bloqueado", None)
        if empresa is None:
            return
        areas = Area.objects.filter(empresa=empresa)
        puestos = Puesto.objects.filter(empresa=empresa)
        if getattr(self.instance, "pk", None) is None:
            areas = areas.filter(activa=True)
            puestos = puestos.filter(activo=True)
        self.fields["area"].queryset = areas
        self.fields["puesto"].queryset = puestos
        supervisores = Usuario.objects.for_empresa(empresa).filter(is_active=True)
        if getattr(self.instance, "pk", None):
            supervisores = supervisores.exclude(pk=self.instance.pk)
        self.fields["supervisor"].queryset = supervisores
        self.fields["area"].required = False
        self.fields["area"].allow_null = True
        self.fields["puesto"].required = False
        self.fields["puesto"].allow_null = True
        self.fields["supervisor"].required = False
        self.fields["supervisor"].allow_null = True

    def validate_email(self, value):
        email = Usuario.objects.normalize_email(value)
        empresa = self.context.get("empresa")
        if empresa is None:
            return email
        qs = Usuario.objects.filter(empresa=empresa, email__iexact=email)
        if getattr(self.instance, "pk", None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este correo en la empresa."
            )
        return email

    def validate(self, attrs):
        empresa = self.context.get("empresa")
        for campo in ("area", "puesto", "supervisor"):
            obj = attrs.get(campo)
            if obj is not None and getattr(obj, "empresa_id", None) not in (None, getattr(empresa, "pk", None)):
                raise serializers.ValidationError(
                    {campo: "Debe pertenecer a la empresa activa."}
                )
        return attrs

    def create(self, validated_data):
        from cuentas.services import asignar_clave_temporal

        empresa = self.context["empresa"]
        usuario = Usuario(
            empresa=empresa,
            must_change_password=True,
            **validated_data,
        )
        clave = asignar_clave_temporal(usuario)
        sincronizar_supervisor(usuario)
        usuario.save()
        usuario.clave_temporal = clave
        return usuario

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        sincronizar_supervisor(instance)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = UsuarioSerializer(instance).data
        clave = getattr(instance, "clave_temporal", None)
        if clave:
            data["clave_temporal"] = clave
        return data


class CambioClaveSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class ResetSolicitudSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetConfirmarSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
