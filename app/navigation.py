"""Menú del shell autenticado según rol. # WP8"""

from django.urls import NoReverseMatch, reverse

from cuentas.models import Usuario


def _ruta(nombre, fallback):
    """Usa la ruta nombrada si existe; si el WP aún no la registró, usa el mapa §6."""
    try:
        return reverse(nombre)
    except NoReverseMatch:
        return fallback


def items_navegacion(user, empresa=None):
    """Lista de links visibles. Un solo menú armado por flags, no plantillas distintas."""
    if user is None or not getattr(user, "is_authenticated", False):
        return []

    rol = getattr(user, "rol", None)
    en_contexto = empresa is not None

    es_superadmin = rol == Usuario.Rol.SUPERADMIN
    es_admin = rol == Usuario.Rol.ADMIN_RRHH or (es_superadmin and en_contexto)
    es_supervisor = rol == Usuario.Rol.SUPERVISOR
    es_empleado = rol == Usuario.Rol.EMPLEADO or es_supervisor

    candidatos = [
        {
            "clave": "dashboard",
            "etiqueta": "Panel",
            "nombre": "app:dashboard",
            "fallback": "/dashboard/",
            "mostrar": True,
        },
        {
            "clave": "empresas",
            "etiqueta": "Empresas",
            "nombre": "empresas:lista",
            "fallback": "/empresas/",
            "mostrar": es_superadmin,
        },
        {
            "clave": "usuarios",
            "etiqueta": "Usuarios",
            "nombre": "cuentas:usuarios",
            "fallback": "/cuentas/usuarios/",
            "mostrar": es_admin,
        },
        {
            "clave": "organigrama",
            "etiqueta": "Organigrama",
            "nombre": "organizacion:organigrama",
            "fallback": "/organizacion/organigrama/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "plantillas",
            "etiqueta": "Plantillas",
            "nombre": "evaluaciones:plantillas",
            "fallback": "/evaluaciones/plantillas/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "ciclos",
            "etiqueta": "Ciclos",
            "nombre": "evaluaciones:ciclos",
            "fallback": "/evaluaciones/ciclos/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "equipo",
            "etiqueta": "Equipo",
            "nombre": "evaluaciones:equipo",
            "fallback": "/evaluaciones/equipo/",
            "mostrar": es_supervisor,
        },
        {
            "clave": "mias",
            "etiqueta": "Mis evaluaciones",
            "nombre": "evaluaciones:mias",
            "fallback": "/evaluaciones/mias/",
            "mostrar": es_empleado,
        },
        {
            "clave": "reportes",
            "etiqueta": "Reportes ISO",
            "nombre": "reportes:iso",
            "fallback": "/reportes/iso/",
            "mostrar": es_admin,
        },
        {
            "clave": "auditoria",
            "etiqueta": "Auditoría",
            "nombre": "auditoria:lista",
            "fallback": "/auditoria/",
            "mostrar": es_admin,
        },
        {
            "clave": "notificaciones",
            "etiqueta": "Notificaciones",
            "nombre": "notificaciones:lista",
            "fallback": "/notificaciones/",
            "mostrar": es_admin or es_supervisor or es_empleado,
        },
        {
            "clave": "perfil",
            "etiqueta": "Perfil",
            "nombre": "cuentas:perfil",
            "fallback": "/cuentas/perfil/",
            "mostrar": True,
        },
    ]

    items = []
    for item in candidatos:
        if not item["mostrar"]:
            continue
        items.append(
            {
                "clave": item["clave"],
                "etiqueta": item["etiqueta"],
                "href": _ruta(item["nombre"], item["fallback"]),
            }
        )
    return items
