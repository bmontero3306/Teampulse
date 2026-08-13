def contexto_sesion(request):
    rol = None
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        rol = getattr(request.user, "rol", None)
    return {
        "empresa_actual": getattr(request, "empresa", None),
        "rol": rol,
        "notificaciones_no_leidas": _contar_notificaciones_no_leidas(request),
    }


def _contar_notificaciones_no_leidas(request):
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return 0
    try:
        from notificaciones.models import Notificacion
    except ImportError:
        return 0
    if not hasattr(Notificacion, "objects"):
        return 0
    try:
        qs = Notificacion.objects.filter(usuario=user, leida=False)
        empresa = getattr(request, "empresa", None)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        return qs.count()
    except Exception:
        return 0


def navegacion(request):
    """Links del sidebar según rol. # WP8"""
    from app.navigation import items_navegacion

    user = getattr(request, "user", None)
    empresa = getattr(request, "empresa", None)
    return {"nav_items": items_navegacion(user, empresa)}
