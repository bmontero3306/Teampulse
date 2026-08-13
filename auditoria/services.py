"""Servicio de trazabilidad. Firma pública estable para WP1/WP2/WP5."""

from datetime import date, datetime
from decimal import Decimal

from django.db import models
from django.http import QueryDict

from auditoria.constants import CLAVES_SENSIBLES
from auditoria.models import AuditLog
from empresas.models import Empresa


def sanitizar_payload(payload):
    """Elimina passwords, tokens y secretos del payload (anidado)."""
    if payload is None:
        return {}
    if isinstance(payload, QueryDict):
        payload = payload.dict()
    return _sanitizar(payload)


def registrar_auditoria(request=None, accion="", instance=None, payload=None, **kwargs):
    """Inserta un AuditLog. No registra passwords ni tokens.

    Firma compatible con el stub de WP0. kwargs extra (usuario, empresa, ip,
    user_agent, obj) se aceptan para no romper a otros agentes.
    """
    instance = instance if instance is not None else kwargs.get("obj")
    usuario = kwargs.get("usuario")
    if usuario is None:
        usuario = _usuario_desde_request(request)

    empresa = _resolver_empresa(request, instance, usuario, kwargs)
    ip = kwargs.get("ip") or _ip_desde_request(request)
    user_agent = kwargs.get("user_agent") or _user_agent_desde_request(request)

    if payload is None:
        payload = _snapshot_instance(instance)
    payload_limpio = sanitizar_payload(payload)

    modelo, object_id = _ref_instancia(instance)

    return AuditLog.objects.create(
        empresa=empresa,
        usuario=usuario if _es_usuario_persistido(usuario) else None,
        accion=accion or "",
        modelo=modelo,
        object_id=object_id,
        payload=payload_limpio,
        ip=ip,
        user_agent=user_agent[:512] if user_agent else "",
    )


def _es_sensible(clave):
    nombre = str(clave).lower().replace("-", "_")
    if nombre in CLAVES_SENSIBLES:
        return True
    return "password" in nombre or "token" in nombre


def _sanitizar(valor):
    if isinstance(valor, dict):
        return {
            str(clave): _sanitizar(item)
            for clave, item in valor.items()
            if not _es_sensible(clave)
        }
    if isinstance(valor, (list, tuple)):
        return [_sanitizar(item) for item in valor]
    return _json_safe(valor)


def _json_safe(valor):
    if valor is None or isinstance(valor, (bool, int, float, str)):
        return valor
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, models.Model):
        return valor.pk
    if isinstance(valor, (bytes, bytearray)):
        return valor.decode("utf-8", errors="replace")
    if isinstance(valor, dict):
        return {str(k): _json_safe(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_safe(v) for v in valor]
    return str(valor)


def _usuario_desde_request(request):
    if request is None:
        return None
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def _es_usuario_persistido(usuario):
    return (
        usuario is not None
        and getattr(usuario, "pk", None) is not None
        and getattr(usuario, "is_authenticated", False)
    )


def _resolver_empresa(request, instance, usuario, kwargs):
    if kwargs.get("empresa") is not None:
        return kwargs["empresa"]
    if request is not None:
        empresa = getattr(request, "empresa", None)
        if empresa is not None:
            return empresa
    if isinstance(instance, Empresa):
        return instance
    if instance is not None:
        empresa = getattr(instance, "empresa", None)
        if empresa is not None:
            return empresa
    if usuario is not None:
        return getattr(usuario, "empresa", None)
    return None


def _ip_desde_request(request):
    if request is None:
        return None
    meta = getattr(request, "META", {}) or {}
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return meta.get("REMOTE_ADDR") or None


def _user_agent_desde_request(request):
    if request is None:
        return ""
    meta = getattr(request, "META", {}) or {}
    return meta.get("HTTP_USER_AGENT") or ""


def _ref_instancia(instance):
    if instance is None or not isinstance(instance, models.Model):
        return "", ""
    modelo = f"{instance._meta.app_label}.{instance._meta.model_name}"
    object_id = str(instance.pk) if instance.pk is not None else ""
    return modelo, object_id


def _snapshot_instance(instance):
    if instance is None or not isinstance(instance, models.Model):
        return {}
    datos = {}
    for field in instance._meta.fields:
        if _es_sensible(field.name):
            continue
        if isinstance(field, (models.FileField, models.BinaryField)):
            continue
        valor = getattr(instance, field.attname, None)
        datos[field.name] = _json_safe(valor)
    return datos
