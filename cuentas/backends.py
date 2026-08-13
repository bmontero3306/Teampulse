from django.contrib.auth.backends import ModelBackend

from cuentas.models import Usuario


class EmailEmpresaBackend(ModelBackend):
    """Autentica por email (no único global) y deja el rechazo fino al formulario."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email") or kwargs.get(Usuario.USERNAME_FIELD)
        if email is None or password is None:
            return None

        candidatos = list(
            Usuario.objects.filter(email__iexact=email).select_related("empresa")
        )
        if not candidatos:
            Usuario().set_password(password)
            return None

        coincidencias = [u for u in candidatos if u.check_password(password)]
        if not coincidencias:
            return None

        for usuario in coincidencias:
            if self._credenciales_permiten_ingreso(usuario):
                return usuario
        return coincidencias[0]

    def get_user(self, user_id):
        try:
            usuario = Usuario.objects.select_related("empresa").get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
        return usuario if self.user_can_authenticate(usuario) else None

    def user_can_authenticate(self, user):
        if user is None or not super().user_can_authenticate(user):
            return False
        return self._credenciales_permiten_ingreso(user)

    def _credenciales_permiten_ingreso(self, usuario):
        if not getattr(usuario, "is_active", False):
            return False
        if getattr(usuario, "bloqueado", False):
            return False
        if getattr(usuario, "rol", None) == Usuario.Rol.SUPERADMIN:
            return True
        empresa = getattr(usuario, "empresa", None)
        if empresa is None:
            return False
        return empresa.estado == empresa.Estado.ACTIVA
