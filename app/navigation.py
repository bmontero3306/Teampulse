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
            "icono": "layout-dashboard",
            "nombre": "app:dashboard",
            "fallback": "/dashboard/",
            "mostrar": True,
        },
        {
            "clave": "empresas",
            "etiqueta": "Empresas",
            "icono": "building-2",
            "nombre": "empresas:lista",
            "fallback": "/empresas/",
            "mostrar": es_superadmin,
        },
        {
            "clave": "usuarios",
            "etiqueta": "Usuarios",
            "icono": "users",
            "nombre": "cuentas:usuarios",
            "fallback": "/cuentas/usuarios/",
            "mostrar": es_admin,
        },
        {
            "clave": "organigrama",
            "etiqueta": "Organigrama",
            "icono": "network",
            "nombre": "organizacion:organigrama",
            "fallback": "/organizacion/organigrama/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "plantillas",
            "etiqueta": "Plantillas",
            "icono": "clipboard-list",
            "nombre": "evaluaciones:plantillas",
            "fallback": "/evaluaciones/plantillas/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "ciclos",
            "etiqueta": "Ciclos",
            "icono": "calendar",
            "nombre": "evaluaciones:ciclos",
            "fallback": "/evaluaciones/ciclos/",
            "mostrar": es_admin or es_supervisor,
        },
        {
            "clave": "equipo",
            "etiqueta": "Equipo",
            "icono": "users-round",
            "nombre": "evaluaciones:equipo",
            "fallback": "/evaluaciones/equipo/",
            "mostrar": es_supervisor,
        },
        {
            "clave": "mias",
            "etiqueta": "Mis evaluaciones",
            "icono": "clipboard-check",
            "nombre": "evaluaciones:mias",
            "fallback": "/evaluaciones/mias/",
            "mostrar": es_empleado,
        },
        {
            "clave": "reportes",
            "etiqueta": "Reportes ISO",
            "icono": "chart-column",
            "nombre": "reportes:iso",
            "fallback": "/reportes/iso/",
            "mostrar": es_admin,
        },
        {
            "clave": "auditoria",
            "etiqueta": "Auditoría",
            "icono": "shield-check",
            "nombre": "auditoria:lista",
            "fallback": "/auditoria/",
            "mostrar": es_admin,
        },
        {
            "clave": "notificaciones",
            "etiqueta": "Notificaciones",
            "icono": "bell",
            "nombre": "notificaciones:lista",
            "fallback": "/notificaciones/",
            "mostrar": es_admin or es_supervisor or es_empleado,
        },
        {
            "clave": "ayuda",
            "etiqueta": "Ayuda",
            "icono": "circle-help",
            "nombre": "app:ayuda",
            "fallback": "/ayuda/",
            "mostrar": True,
        },
        {
            "clave": "perfil",
            "etiqueta": "Perfil",
            "icono": "circle-user",
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
                "icono": item["icono"],
                "href": _ruta(item["nombre"], item["fallback"]),
            }
        )
    return items
