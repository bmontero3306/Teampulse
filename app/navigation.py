"""Menú del shell autenticado según rol. # WP8"""

from cuentas.models import Usuario


def items_navegacion(user, empresa=None):
    """Lista de links visibles. Paths de la SPA, sin rutas HTML."""
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
            "icono": "layout-dashboard",
            "href": "/dashboard",
            "mostrar": True,
        },
        {
            "clave": "empresas",
            "etiqueta": "Empresas",
            "icono": "building-2",
            "href": "/empresas",
            "mostrar": es_superadmin,
        },
        {
            "clave": "usuarios",
            "etiqueta": "Usuarios",
            "icono": "users",
            "href": "/usuarios",
            "mostrar": es_admin,
        },
        {
            "clave": "organigrama",
            "etiqueta": "Organigrama",
            "icono": "network",
            "href": "/organizacion",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "plantillas",
            "etiqueta": "Plantillas",
            "icono": "clipboard-list",
            "href": "/evaluaciones/plantillas",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "ciclos",
            "etiqueta": "Ciclos",
            "icono": "calendar",
            "href": "/evaluaciones/ciclos",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "equipo",
            "etiqueta": "Equipo",
            "icono": "users-round",
            "href": "/evaluaciones/equipo",
            "mostrar": es_supervisor,
        },
        {
            "clave": "mias",
            "etiqueta": "Mis evaluaciones",
            "icono": "clipboard-check",
            "href": "/evaluaciones/mias",
            "mostrar": es_empleado,
        },
        {
            "clave": "reportes",
            "etiqueta": "Reportes",
            "icono": "chart-column",
            "href": "/reportes/iso",
            "mostrar": es_admin,
        },
        {
            "clave": "auditoria",
            "etiqueta": "Auditoría",
            "icono": "shield-check",
            "href": "/auditoria",
            "mostrar": es_admin,
        },
        {
            "clave": "notificaciones",
            "etiqueta": "Notificaciones",
            "icono": "bell",
            "href": "/notificaciones",
            "mostrar": es_admin or es_supervisor or es_empleado,
        },
        {
            "clave": "ayuda",
            "etiqueta": "Ayuda",
            "icono": "circle-help",
            "href": "/ayuda",
            "mostrar": True,
        },
        {
            "clave": "perfil",
            "etiqueta": "Perfil",
            "icono": "circle-user",
            "href": "/perfil",
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
                "icono": item["icono"],
                "href": item["href"],
            }
        )
    return items
