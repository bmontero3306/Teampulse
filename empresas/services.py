"""Servicios de empresas: CUIT y transiciones de estado."""

from django.db.utils import OperationalError, ProgrammingError

from empresas.models import Empresa
from empresas.validators import formatear_cuit, normalizar_cuit, validar_cuit

__all__ = [
    "activar_empresa",
    "auditar_empresa",
    "cambiar_estado",
    "formatear_cuit",
    "inactivar_empresa",
    "normalizar_cuit",
    "suspender_empresa",
    "validar_cuit",
]


def auditar_empresa(request, accion, instance, payload=None):
    """Delega en auditoria.services. Si WP9 aún no migró la tabla, no rompe el CRUD."""
    from auditoria.services import registrar_auditoria

    try:
        return registrar_auditoria(request, accion, instance, payload=payload)
    except (OperationalError, ProgrammingError):
        return None


def cambiar_estado(empresa, nuevo_estado, request=None, accion=None):
    """Cambia el estado sin borrar datos ni usuarios."""
    anterior = empresa.estado
    if anterior == nuevo_estado:
        return empresa
    empresa.estado = nuevo_estado
    empresa.save(update_fields=["estado", "updated_at"])
    if accion is None:
        accion = f"empresa_{nuevo_estado}"
    auditar_empresa(
        request,
        accion,
        empresa,
        payload={"estado_anterior": anterior, "estado_nuevo": nuevo_estado},
    )
    return empresa


def suspender_empresa(empresa, request=None):
    """Pasa a suspendida. Los usuarios no podrán loguear (chequeo de login: WP2)."""
    return cambiar_estado(
        empresa,
        Empresa.Estado.SUSPENDIDA,
        request=request,
        accion="empresa_suspension",
    )


def activar_empresa(empresa, request=None):
    return cambiar_estado(
        empresa,
        Empresa.Estado.ACTIVA,
        request=request,
        accion="empresa_activacion",
    )


def inactivar_empresa(empresa, request=None):
    """Pasa a inactiva sin borrar datos."""
    return cambiar_estado(
        empresa,
        Empresa.Estado.INACTIVA,
        request=request,
        accion="empresa_inactivacion",
    )
