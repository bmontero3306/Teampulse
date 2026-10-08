from rest_framework import serializers

from empresas.forms import EmpresaFichaForm, EmpresaForm
from empresas.models import Empresa


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

    def validate(self, attrs):
        request = self.context["request"]
        es_ficha = (
            self.instance is not None
            and getattr(request.user, "rol", None) != "superadmin"
        )
        form_cls = EmpresaFichaForm if es_ficha else EmpresaForm
        data = {}
        if self.instance is not None:
            for field in form_cls.Meta.fields:
                data[field] = attrs.get(field, getattr(self.instance, field))
        else:
            data = {field: attrs.get(field) for field in form_cls.Meta.fields}
        form = form_cls(data=data, instance=self.instance)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        attrs.update(form.cleaned_data)
        if es_ficha:
            for campo in ("razon_social", "cuit", "estado"):
                attrs.pop(campo, None)
        return attrs
