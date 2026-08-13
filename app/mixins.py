from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RolRequiredMixin(LoginRequiredMixin):
    """Exige autenticación y que request.user.rol esté en roles_permitidos."""

    roles_permitidos: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.roles_permitidos and getattr(request.user, "rol", None) not in self.roles_permitidos:
            raise PermissionDenied("No tenés permiso para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)


class EmpresaRequiredMixin(LoginRequiredMixin):
    """Exige autenticación y un request.empresa activo."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request, "empresa", None) is None:
            raise PermissionDenied("No hay una empresa activa en el contexto.")
        return super().dispatch(request, *args, **kwargs)
