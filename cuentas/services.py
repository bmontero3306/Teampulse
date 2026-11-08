from django.utils.crypto import get_random_string


def generar_clave_temporal():
    return get_random_string(12, "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") + "-Tp1"


def asignar_clave_temporal(usuario):
    clave = generar_clave_temporal()
    usuario.set_password(clave)
    usuario.must_change_password = True
    return clave


def usuarios_para_recuperar_clave(email):
    from cuentas.models import Usuario
    from empresas.models import Empresa

    candidatos = Usuario.objects.filter(
        email__iexact=email,
        is_active=True,
        bloqueado=False,
    ).select_related("empresa")
    elegibles = []
    for usuario in candidatos:
        if not usuario.has_usable_password():
            continue
        if usuario.rol == Usuario.Rol.SUPERADMIN:
            elegibles.append(usuario)
            continue
        empresa = usuario.empresa
        if empresa is not None and empresa.estado == Empresa.Estado.ACTIVA:
            elegibles.append(usuario)
    return elegibles


def sincronizar_supervisor(usuario):
    """Deriva el supervisor del ocupante de puesto.puesto_superior.

    Si el modelo Puesto o los usuarios no están listos, no crashea.
    """
    try:
        puesto = getattr(usuario, "puesto", None)
        if puesto is None:
            return getattr(usuario, "supervisor", None)

        puesto_superior_id = getattr(puesto, "puesto_superior_id", None)
        if not puesto_superior_id:
            return getattr(usuario, "supervisor", None)

        from cuentas.models import Usuario

        ocupantes = Usuario.objects.filter(
            puesto_id=puesto_superior_id,
            is_active=True,
        )
        pk = getattr(usuario, "pk", None)
        if pk:
            ocupantes = ocupantes.exclude(pk=pk)
        empresa_id = getattr(usuario, "empresa_id", None)
        if empresa_id:
            ocupantes = ocupantes.filter(empresa_id=empresa_id)

        ocupante = ocupantes.first()
        if ocupante is not None:
            usuario.supervisor = ocupante
        return getattr(usuario, "supervisor", None)
    except Exception:
        return getattr(usuario, "supervisor", None)
