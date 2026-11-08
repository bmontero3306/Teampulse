from cuentas.models import Usuario


ROLES_LECTURA = [
    Usuario.Rol.SUPERADMIN,
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
    Usuario.Rol.EMPLEADO,
]
ROLES_CRUD = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]


def puede_editar_organizacion(user):
    return getattr(user, "rol", None) in ROLES_CRUD


def _puesto_usuario(user):
    return getattr(user, "puesto", None)


def _area_usuario(user):
    area = getattr(user, "area", None)
    if area is not None:
        return area
    puesto = _puesto_usuario(user)
    return getattr(puesto, "area", None) if puesto is not None else None


def _filtrar_puestos_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activo=True)
        return qs
    puesto = _puesto_usuario(user)
    if puesto is None:
        return qs.none()
    return qs.filter(pk=puesto.pk)


def _filtrar_areas_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activa=True)
        return qs
    area = _area_usuario(user)
    if area is None:
        return qs.none()
    return qs.filter(pk=area.pk)


def _filtrar_competencias_lectura(qs, user):
    if user.rol != Usuario.Rol.EMPLEADO:
        if user.rol == Usuario.Rol.SUPERVISOR:
            return qs.filter(activa=True)
        return qs
    if _puesto_usuario(user) is None:
        return qs.none()
    return qs.filter(activa=True)
