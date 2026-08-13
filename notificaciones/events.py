"""Tipos de evento de notificación (RF5 / §3.6)."""

USUARIO_CREADO = "usuario_creado"
USUARIO_MODIFICADO = "usuario_modificado"
CUENTA_RESET = "cuenta_reset"
CUENTA_BLOQUEO = "cuenta_bloqueo"
CICLO_ACTIVADO = "ciclo_activado"
AUTOEVALUACION_ENVIADA = "autoevaluacion_enviada"
EVALUACION_SUPERVISOR_CERRADA = "evaluacion_supervisor_cerrada"
CONFORMIDAD_FIRMADA = "conformidad_firmada"
CONFORMIDAD_OBSERVACION = "conformidad_observacion"
CICLO_PAUSADO = "ciclo_pausado"
CICLO_CANCELADO = "ciclo_cancelado"
CICLO_REPROGRAMADO = "ciclo_reprogramado"
RECORDATORIO_VENCIMIENTO = "recordatorio_vencimiento"

TIPOS = (
    (USUARIO_CREADO, "Usuario creado"),
    (USUARIO_MODIFICADO, "Datos de usuario modificados"),
    (CUENTA_RESET, "Reset de cuenta"),
    (CUENTA_BLOQUEO, "Bloqueo de cuenta"),
    (CICLO_ACTIVADO, "Ciclo activado"),
    (AUTOEVALUACION_ENVIADA, "Autoevaluación enviada"),
    (EVALUACION_SUPERVISOR_CERRADA, "Evaluación de supervisor cerrada"),
    (CONFORMIDAD_FIRMADA, "Conformidad firmada"),
    (CONFORMIDAD_OBSERVACION, "Observación de disconformidad"),
    (CICLO_PAUSADO, "Ciclo pausado"),
    (CICLO_CANCELADO, "Ciclo cancelado"),
    (CICLO_REPROGRAMADO, "Ciclo reprogramado"),
    (RECORDATORIO_VENCIMIENTO, "Recordatorio de vencimiento"),
)

TIPO_CHOICES = TIPOS


class _ContextoSeguro(dict):
    def __missing__(self, key):
        return ""


PLANTILLAS = {
    USUARIO_CREADO: {
        "titulo": "Tu cuenta en TeamPulse fue creada",
        "mensaje": (
            "Hola {nombre}. Se creó tu usuario en {empresa}. "
            "Ya podés iniciar sesión con tu correo."
        ),
    },
    USUARIO_MODIFICADO: {
        "titulo": "Se actualizaron tus datos",
        "mensaje": (
            "Hola {nombre}. Un administrador actualizó los datos de tu cuenta "
            "en {empresa}."
        ),
    },
    CUENTA_RESET: {
        "titulo": "Se restableció tu contraseña",
        "mensaje": (
            "Hola {nombre}. Se inició un restablecimiento de contraseña para "
            "tu cuenta. Si no lo pediste, contactá a RRHH."
        ),
    },
    CUENTA_BLOQUEO: {
        "titulo": "Tu cuenta fue bloqueada",
        "mensaje": (
            "Hola {nombre}. Tu acceso a TeamPulse fue bloqueado. "
            "Contactá a RRHH si necesitás recuperarlo."
        ),
    },
    CICLO_ACTIVADO: {
        "titulo": "Se activó un ciclo de evaluación",
        "mensaje": (
            "El ciclo «{ciclo}» está activo. Fecha de cierre: {fecha_cierre}. "
            "Completá tus pendientes a tiempo."
        ),
    },
    AUTOEVALUACION_ENVIADA: {
        "titulo": "Autoevaluación enviada",
        "mensaje": (
            "{evaluado} envió su autoevaluación del ciclo «{ciclo}». "
            "Ya podés completarla como supervisor."
        ),
    },
    EVALUACION_SUPERVISOR_CERRADA: {
        "titulo": "Tu evaluación de supervisor está lista",
        "mensaje": (
            "El supervisor cerró tu evaluación del ciclo «{ciclo}». "
            "Revisá el resultado y firmá la conformidad."
        ),
    },
    CONFORMIDAD_FIRMADA: {
        "titulo": "Conformidad firmada",
        "mensaje": (
            "{evaluado} firmó la conformidad de su evaluación del ciclo «{ciclo}»."
        ),
    },
    CONFORMIDAD_OBSERVACION: {
        "titulo": "Observación de disconformidad",
        "mensaje": (
            "{evaluado} registró una observación de disconformidad en el ciclo "
            "«{ciclo}»."
        ),
    },
    CICLO_PAUSADO: {
        "titulo": "Ciclo de evaluación pausado",
        "mensaje": "El ciclo «{ciclo}» fue pausado. Te avisaremos cuando se retome.",
    },
    CICLO_CANCELADO: {
        "titulo": "Ciclo de evaluación cancelado",
        "mensaje": "El ciclo «{ciclo}» fue cancelado. No hace falta completar pendientes.",
    },
    CICLO_REPROGRAMADO: {
        "titulo": "Ciclo de evaluación reprogramado",
        "mensaje": (
            "El ciclo «{ciclo}» cambió de fechas. Nuevo cierre: {fecha_cierre}."
        ),
    },
    RECORDATORIO_VENCIMIENTO: {
        "titulo": "Recordatorio: evaluación por vencer",
        "mensaje": (
            "Tenés pendientes en el ciclo «{ciclo}». Fecha de cierre: {fecha_cierre}."
        ),
    },
}


def resolver_contenido(tipo, contexto=None):
    """Devuelve (titulo, mensaje, url) a partir del tipo y un dict de contexto."""
    contexto = _ContextoSeguro(contexto or {})
    plantilla = PLANTILLAS.get(tipo) or {}
    titulo = plantilla.get("titulo", "")
    mensaje = plantilla.get("mensaje", "")
    try:
        titulo = titulo.format_map(contexto)
        mensaje = mensaje.format_map(contexto)
    except (ValueError, KeyError):
        pass
    url = contexto.get("url") or ""
    return titulo, mensaje, url
