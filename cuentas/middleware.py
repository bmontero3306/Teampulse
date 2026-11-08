from django.http import JsonResponse

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
