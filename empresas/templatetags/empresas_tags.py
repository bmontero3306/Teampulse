from django import template

from cuentas.models import Usuario
from empresas.models import Empresa
from empresas.validators import formatear_cuit

register = template.Library()


@register.filter
def cuit_formato(value):
    return formatear_cuit(value)


@register.simple_tag(takes_context=True)
def empresas_para_selector(context):
    request = context.get("request")
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return Empresa.objects.none()
    if getattr(user, "rol", None) != Usuario.Rol.SUPERADMIN:
        return Empresa.objects.none()
    return Empresa.objects.all().order_by("nombre")
