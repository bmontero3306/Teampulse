from django.shortcuts import redirect
from django.urls import Resolver404, resolve


class MustChangePasswordMiddleware:
    """Fuerza el cambio de clave cuando must_change_password es True."""

    EXENTAS = {
        "cuentas:login",
        "cuentas:logout",
        "cuentas:password_change",
        "cuentas:password_reset",
        "cuentas:password_reset_done",
        "cuentas:password_reset_confirm",
    }
    PREFIJOS_EXENTOS = ("/static/", "/admin/", "/__reload__/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "must_change_password", False)
            and not self._esta_exenta(request)
        ):
            return redirect("cuentas:password_change")
        return self.get_response(request)

    def _esta_exenta(self, request):
        path = request.path_info or request.path
        if any(path.startswith(prefijo) for prefijo in self.PREFIJOS_EXENTOS):
            return True
        try:
            match = resolve(path)
        except Resolver404:
            return False
        nombre = match.url_name or ""
        if match.namespace:
            nombre = f"{match.namespace}:{nombre}"
        return nombre in self.EXENTAS
