class Accion:
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FALLIDO = "login_fallido"
    CREAR = "crear"
    EDITAR = "editar"
    ELIMINAR = "eliminar"
    DESACTIVAR = "desactivar"
    SUSPENDER = "suspender"
    ACTIVAR = "activar"
    EXPORTAR = "exportar"
    FIRMAR = "firmar"


ACCION_LABELS = {
    Accion.LOGIN: "Inicio de sesión",
    Accion.LOGOUT: "Cierre de sesión",
    Accion.LOGIN_FALLIDO: "Login fallido",
    Accion.CREAR: "Alta",
    Accion.EDITAR: "Edición",
    Accion.ELIMINAR: "Eliminación",
    Accion.DESACTIVAR: "Desactivación",
    Accion.SUSPENDER: "Suspensión",
    Accion.ACTIVAR: "Activación",
    Accion.EXPORTAR: "Exportación",
    Accion.FIRMAR: "Firma",
}

CLAVES_SENSIBLES = frozenset(
    {
        "password",
        "password1",
        "password2",
        "passwd",
        "pwd",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "csrf",
        "csrfmiddlewaretoken",
        "sessionid",
        "clave",
        "nueva_clave",
        "clave_actual",
        "token_key",
    }
)
