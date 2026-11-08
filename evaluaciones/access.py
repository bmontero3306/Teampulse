from cuentas.models import Usuario
from evaluaciones.services import _es_rrhh

ROLES_LECTURA = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
]
ROLES_CRUD = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]
ROLES_FLUJO_PROPIO = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
    Usuario.Rol.EMPLEADO,
]
ROLES_SUPERVISOR = [Usuario.Rol.SUPERVISOR]


def puede_editar_plantillas(user):
    return getattr(user, "rol", None) in ROLES_CRUD


def puede_gestionar_ciclos(user):
    return getattr(user, "rol", None) in ROLES_CRUD


def _ip(request):
    meta = getattr(request, "META", {}) or {}
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return meta.get("REMOTE_ADDR") or None


def _puede_ver_resultado(user, evaluacion):
    if evaluacion.evaluado_id == user.pk:
        return True
    if not evaluacion.comparacion_revelada:
        return False
    if evaluacion.evaluador_id == user.pk:
        return True
    return _es_rrhh(user)
