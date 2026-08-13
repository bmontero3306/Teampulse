from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from auditoria.constants import Accion
from auditoria.services import registrar_auditoria


@receiver(user_logged_in, dispatch_uid="auditoria.user_logged_in")
def on_user_logged_in(sender, request, user, **kwargs):
    registrar_auditoria(
        request,
        Accion.LOGIN,
        user,
        payload={"email": getattr(user, "email", "")},
    )


@receiver(user_logged_out, dispatch_uid="auditoria.user_logged_out")
def on_user_logged_out(sender, request, user, **kwargs):
    registrar_auditoria(
        request,
        Accion.LOGOUT,
        user,
        payload={"email": getattr(user, "email", "") if user is not None else ""},
        usuario=user if user is not None and getattr(user, "pk", None) else None,
    )


@receiver(user_login_failed, dispatch_uid="auditoria.user_login_failed")
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    email = ""
    if isinstance(credentials, dict):
        email = credentials.get("email") or credentials.get("username") or ""
    registrar_auditoria(
        request,
        Accion.LOGIN_FALLIDO,
        None,
        payload={"email": email},
    )
