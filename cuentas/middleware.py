from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from cuentas.backends import EmailEmpresaBackend


class TokenAuthMiddleware:
    """Carga request.user desde Authorization: Token antes del middleware de empresa.

    DRF autentica otra vez en la vista. Sin esto, EmpresaMiddleware no ve al usuario
    porque la sesión no existe en la SPA.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            header = request.META.get("HTTP_AUTHORIZATION", "")
            if header.startswith("Token "):
                key = header.split(" ", 1)[1].strip()
                token_user = self._usuario_desde_token(key)
                if token_user is not None:
                    request.user = token_user
        return self.get_response(request)

    def _usuario_desde_token(self, key):
        if not key:
            return None
        from rest_framework.authtoken.models import Token

        try:
            token = Token.objects.select_related("user", "user__empresa").get(key=key)
        except Token.DoesNotExist:
            return None
        if EmailEmpresaBackend().user_can_authenticate(token.user):
            return token.user
        return None


class MustChangePasswordApiMiddleware:
    """403 JSON en /api/ si falta cambiar la clave. No depende de permission_classes."""

    EXENTAS = {
        "/api/v1/auth/login/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/me/",
        "/api/v1/auth/password/change/",
        "/api/v1/auth/password/reset/",
        "/api/v1/auth/password/reset/confirm/",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or request.path
        user = getattr(request, "user", None)
        if (
            path.startswith("/api/")
            and path not in self.EXENTAS
            and user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "must_change_password", False)
        ):
            return JsonResponse(
                {
                    "detail": {
                        "code": "must_change_password",
                        "detail": "Tenés que cambiar la contraseña antes de continuar.",
                    }
                },
                status=403,
            )
        return self.get_response(request)


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
    PREFIJOS_EXENTOS = ("/static/", "/admin/", "/api/", "/__reload__/")

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
