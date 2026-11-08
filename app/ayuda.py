"""Catálogo de la sección Ayuda. El contenido vive en plantillas por slug."""

from cuentas.models import Usuario

ROLES_GESTION = (
    Usuario.Rol.ADMIN_RRHH,
    Usuario.Rol.SUPERVISOR,
    Usuario.Rol.SUPERADMIN,
)
ROLES_RRHH = (Usuario.Rol.ADMIN_RRHH, Usuario.Rol.SUPERADMIN)
ROLES_SUPERADMIN = (Usuario.Rol.SUPERADMIN,)

PAGINAS = [
    {
        "slug": "inicio",
        "titulo": "Cómo funciona TeamPulse",
        "resumen": "Qué es el sistema, qué piezas hay y en qué orden se usa.",
        "icono": "book-open",
        "grupo": "Empezar",
        "roles": None,
        "requiere_empresa": False,
    },
    {
        "slug": "roles",
        "titulo": "Roles y permisos",
        "resumen": "Qué puede hacer cada rol y qué ve en el menú.",
        "icono": "shield",
        "grupo": "Empezar",
        "roles": None,
        "requiere_empresa": False,
    },
    {
        "slug": "organizacion",
        "titulo": "Organización",
        "resumen": "Empresas, áreas, puestos, organigrama y competencias.",
        "icono": "network",
        "grupo": "Configuración",
        "roles": ROLES_GESTION,
        "requiere_empresa": False,
    },
    {
        "slug": "plantillas",
        "titulo": "Plantillas de evaluación",
        "resumen": "Criterios, escalas, ponderaciones y asignación a puestos.",
        "icono": "clipboard-list",
        "grupo": "Configuración",
        "roles": ROLES_GESTION,
        "requiere_empresa": False,
    },
    {
        "slug": "ciclos",
        "titulo": "Ciclos de evaluación",
        "resumen": "Estados del ciclo, activación, pausa, cierre y participantes.",
        "icono": "calendar",
        "grupo": "Configuración",
        "roles": ROLES_GESTION,
        "requiere_empresa": False,
    },
    {
        "slug": "flujo",
        "titulo": "Flujo de una evaluación",
        "resumen": "Estados, quién actúa en cada paso y qué pasa después.",
        "icono": "git-branch",
        "grupo": "Evaluación",
        "roles": None,
        "requiere_empresa": False,
    },
    {
        "slug": "conformidad",
        "titulo": "Firma y conformidad",
        "resumen": "Reunión de feedback, firma, observación y comprobante.",
        "icono": "pen-line",
        "grupo": "Evaluación",
        "roles": None,
        "requiere_empresa": False,
    },
    {
        "slug": "notificaciones",
        "titulo": "Notificaciones",
        "resumen": "Avisos in-app, email y recordatorios de vencimiento.",
        "icono": "bell",
        "grupo": "Seguimiento",
        "roles": None,
        "requiere_empresa": False,
    },
    {
        "slug": "reportes",
        "titulo": "Reportes",
        "resumen": "Filtros, exportación PDF/Excel y trazabilidad de la exportación.",
        "icono": "chart-column",
        "grupo": "Seguimiento",
        "roles": ROLES_RRHH,
        "requiere_empresa": False,
    },
    {
        "slug": "auditoria",
        "titulo": "Auditoría",
        "resumen": "Qué se registra, quién puede verlo y qué datos se ocultan.",
        "icono": "shield-check",
        "grupo": "Seguimiento",
        "roles": ROLES_RRHH,
        "requiere_empresa": False,
    },
    {
        "slug": "empresas",
        "titulo": "Empresas y plataforma",
        "resumen": "Tenants, estados de empresa y selector de contexto.",
        "icono": "building-2",
        "grupo": "Plataforma",
        "roles": ROLES_SUPERADMIN,
        "requiere_empresa": False,
    },
]


def _es_visible(pagina, user, empresa=None):
    roles = pagina["roles"]
    if roles is not None and getattr(user, "rol", None) not in roles:
        return False
    if pagina.get("requiere_empresa") and empresa is None:
        return False
    return True


def paginas_visibles(user, empresa=None):
    return [p for p in PAGINAS if _es_visible(p, user, empresa)]


def pagina_por_slug(slug):
    for pagina in PAGINAS:
        if pagina["slug"] == slug:
            return pagina
    return None


def grupos_paginas(user, empresa=None):
    grupos = []
    vistos = {}
    for pagina in paginas_visibles(user, empresa):
        nombre = pagina["grupo"]
        if nombre not in vistos:
            vistos[nombre] = len(grupos)
            grupos.append({"nombre": nombre, "paginas": []})
        grupos[vistos[nombre]]["paginas"].append(pagina)
    return grupos
