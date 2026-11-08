from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from cuentas.models import Usuario
from empresas.models import Empresa
from empresas.validators import validar_cuit

CAMPOS_FICHA = ("nombre", "email_contacto", "telefono", "direccion")
CAMPOS_PROTEGIDOS = ("razon_social", "cuit", "estado")


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = (
            "id",
            "nombre",
            "razon_social",
            "cuit",
            "email_contacto",
            "telefono",
            "direccion",
            "estado",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def _es_ficha(self):
        if self.instance is None:
            return False
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        return rol != Usuario.Rol.SUPERADMIN

    def to_internal_value(self, data):
        if self._es_ficha() and hasattr(data, "items"):
            data = {clave: valor for clave, valor in data.items() if clave in CAMPOS_FICHA}
        return super().to_internal_value(data)

    def validate_cuit(self, value):
        try:
            cuit = validar_cuit(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        qs = Empresa.objects.filter(cuit=cuit)
        if self.instance is not None and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una empresa con este CUIT.")
        return cuit

    def validate(self, attrs):
        if self._es_ficha():
            for campo in CAMPOS_PROTEGIDOS:
                attrs.pop(campo, None)
        return attrs
