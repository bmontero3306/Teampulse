"""Asigna request.empresa a partir del usuario autenticado."""


class EmpresaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            empresa = getattr(user, "empresa", None)
            rol = getattr(user, "rol", None)
            if rol == "superadmin":
                # La SPA manda el tenant en el header; la sesión queda para /admin/.
                empresa_id = request.META.get("HTTP_X_EMPRESA_ID") or request.session.get(
                    "empresa_id"
                )
                if isinstance(empresa_id, str):
                    empresa_id = empresa_id.strip() or None
                if empresa_id is not None:
                    try:
                        empresa_id = int(empresa_id)
                    except (TypeError, ValueError):
                        empresa_id = None
                if empresa_id:
                    from empresas.models import Empresa

                    empresa = Empresa.objects.filter(pk=empresa_id).first() or empresa
            request.empresa = empresa
        return self.get_response(request)
