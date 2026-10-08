from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission


class MustChangePassword(APIException):
    status_code = 403
    default_code = "must_change_password"
    default_detail = {
        "code": "must_change_password",
        "detail": "Tenés que cambiar la contraseña antes de continuar.",
    }


class MustChangePasswordPermission(BasePermission):
    """Bloquea la API si el usuario debe cambiar la clave, salvo vistas marcadas."""

    def has_permission(self, request, view):
        if getattr(view, "permite_clave_pendiente", False):
            return True
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return True
        if getattr(user, "must_change_password", False):
            raise MustChangePassword()
        return True


class RolPermission(BasePermission):
    """Exige que request.user.rol esté en view.roles_permitidos."""

    message = "No tenés permiso para acceder a esta sección."

    def has_permission(self, request, view):
        roles = getattr(view, "roles_permitidos", None) or []
        if not roles:
            return True
        return getattr(request.user, "rol", None) in roles


class EmpresaActivaPermission(BasePermission):
    message = "No hay una empresa activa en el contexto."

    def has_permission(self, request, view):
        return getattr(request, "empresa", None) is not None


def roles(*codigos):
    """Permiso con la lista de roles cerrada en la clase."""

    class _Rol(RolPermission):
        def has_permission(self, request, view):
            return getattr(request.user, "rol", None) in codigos

    _Rol.__name__ = "Rol_" + "_".join(codigos)
    return _Rol
