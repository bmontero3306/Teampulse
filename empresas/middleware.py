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
                empresa_id = request.session.get("empresa_id")
                if empresa_id:
                    from empresas.models import Empresa

                    empresa = Empresa.objects.filter(pk=empresa_id).first() or empresa
            request.empresa = empresa
        return self.get_response(request)
