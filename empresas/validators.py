"""Validación de CUIT argentino (formato: 11 dígitos, con o sin guiones)."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

_CUIT_SEP = re.compile(r"[^\d\s.\-]")
_SOLO_DIGITOS = re.compile(r"\D")


def normalizar_cuit(cuit: str | None) -> str:
    """Devuelve solo los dígitos del CUIT."""
    if cuit is None:
        return ""
    return _SOLO_DIGITOS.sub("", str(cuit).strip())


def formatear_cuit(cuit: str | None) -> str:
    """Formato de visualización XX-XXXXXXXX-X."""
    digitos = normalizar_cuit(cuit)
    if len(digitos) != 11:
        return cuit or ""
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


def validar_cuit(cuit: str | None) -> str:
    """Valida formato AR (11 dígitos / con guiones). Devuelve el CUIT normalizado.

    Función pura respecto del modelo: no toca la base. Lanza ValidationError.
    """
    if cuit is None:
        raise ValidationError("Ingresá un CUIT.", code="required")
    crudo = str(cuit).strip()
    if not crudo:
        raise ValidationError("Ingresá un CUIT.", code="required")
    if _CUIT_SEP.search(crudo):
        raise ValidationError(
            "El CUIT solo puede contener números y guiones.",
            code="invalid",
        )
    digitos = normalizar_cuit(crudo)
    if len(digitos) != 11:
        raise ValidationError(
            "El CUIT debe tener 11 dígitos (con o sin guiones).",
            code="invalid",
        )
    return digitos
