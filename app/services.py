"""Consultas agregadas del dashboard (WP8). Solo consume modelos de WP5."""

from django.db.models import Count, Q
from django.urls import NoReverseMatch, reverse

from evaluaciones.models import CicloEvaluacion, Evaluacion

ESTADOS_AUTO = [
    Evaluacion.Estado.SUPERVISOR,
    Evaluacion.Estado.PENDIENTE_REUNION,
    Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
    Evaluacion.Estado.CERRADA,
]
ESTADOS_SUPERVISOR = [
    Evaluacion.Estado.PENDIENTE_REUNION,
    Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
    Evaluacion.Estado.CERRADA,
]
ESTADOS_FIRMADAS = [
    Evaluacion.Estado.CERRADA,
]
ESTADOS_SIN_AUTO = [
    Evaluacion.Estado.AUTOEVALUACION,
]
ESTADOS_PENDIENTE_EMPLEADO = [
    Evaluacion.Estado.AUTOEVALUACION,
    Evaluacion.Estado.PENDIENTE_REUNION,
    Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
]

KPIS_VACIOS = {
    "participantes": 0,
    "auto": 0,
    "supervisor": 0,
    "firmadas": 0,
    "sin_evaluador": 0,
}


def _ruta(nombre, fallback, args=None):
    try:
        return reverse(nombre, args=args) if args else reverse(nombre)
    except NoReverseMatch:
        return fallback


def ciclo_activo(empresa):
    if empresa is None:
        return None
    return (
        CicloEvaluacion.objects.for_empresa(empresa)
        .filter(estado=CicloEvaluacion.Estado.ACTIVO)
        .first()
    )


def kpis_ciclo(empresa, ciclo):
    """KPIs del ciclo activo: participantes, auto, supervisor, firmadas, sin evaluador."""
    if empresa is None or ciclo is None:
        return dict(KPIS_VACIOS)
    return (
        Evaluacion.objects.for_empresa(empresa)
        .filter(ciclo=ciclo)
        .aggregate(
            participantes=Count("pk"),
            auto=Count("pk", filter=Q(estado__in=ESTADOS_AUTO)),
            supervisor=Count("pk", filter=Q(estado__in=ESTADOS_SUPERVISOR)),
            firmadas=Count("pk", filter=Q(estado__in=ESTADOS_FIRMADAS)),
            sin_evaluador=Count("pk", filter=Q(sin_evaluador=True)),
        )
    )


def pendientes_empleado(user, empresa, ciclo):
    """Autoevaluación y conformidad pendientes del usuario en el ciclo activo."""
    if user is None or empresa is None or ciclo is None:
        return []
    qs = (
        Evaluacion.objects.for_empresa(empresa)
        .filter(
            ciclo=ciclo,
            evaluado=user,
            estado__in=ESTADOS_PENDIENTE_EMPLEADO,
        )
        .select_related("ciclo", "evaluado")
        .prefetch_related("respuestas")
    )
    items = []
    for evaluacion in qs:
        if evaluacion.estado in ESTADOS_SIN_AUTO:
            items.append(
                {
                    "evaluacion": evaluacion,
                    "tipo": "auto",
                    "accion": "Completar autoevaluación",
                    "href": _ruta(
                        "evaluaciones:auto",
                        f"/evaluaciones/{evaluacion.pk}/autoevaluacion/",
                        args=[evaluacion.pk],
                    ),
                }
            )
        elif evaluacion.estado == Evaluacion.Estado.PENDIENTE_REUNION:
            items.append(
                {
                    "evaluacion": evaluacion,
                    "tipo": "comparacion",
                    "accion": "Ver comparación",
                    "href": _ruta(
                        "evaluaciones:resultado",
                        f"/evaluaciones/{evaluacion.pk}/resultado/",
                        args=[evaluacion.pk],
                    ),
                }
            )
        else:
            items.append(
                {
                    "evaluacion": evaluacion,
                    "tipo": "firma",
                    "accion": "Firmar conformidad",
                    "href": _ruta(
                        "evaluaciones:resultado",
                        f"/evaluaciones/{evaluacion.pk}/resultado/",
                        args=[evaluacion.pk],
                    ),
                }
            )
    return items


def accesos_rapidos_empleado(pendientes):
    accesos = [
        {
            "clave": "mias",
            "etiqueta": "Mis evaluaciones",
            "href": _ruta("evaluaciones:mias", "/evaluaciones/mias/"),
        }
    ]
    auto = next((item for item in pendientes if item["tipo"] == "auto"), None)
    comparacion = next((item for item in pendientes if item["tipo"] == "comparacion"), None)
    firma = next((item for item in pendientes if item["tipo"] == "firma"), None)
    if auto:
        accesos.append(
            {
                "clave": "auto",
                "etiqueta": "Autoevaluación",
                "href": auto["href"],
            }
        )
    if comparacion:
        accesos.append(
            {
                "clave": "comparacion",
                "etiqueta": "Ver comparación",
                "href": comparacion["href"],
            }
        )
    if firma:
        accesos.append(
            {
                "clave": "firmar",
                "etiqueta": "Firmar conformidad",
                "href": firma["href"],
            }
        )
    return accesos


def resumen_equipo(user, empresa, ciclo):
    """Equipo a cargo, % de autoevaluaciones hechas y alertas sin autoevaluación."""
    vacio = {
        "evaluaciones": [],
        "total": 0,
        "auto_hechas": 0,
        "completitud": 0,
        "alertas_sin_auto": [],
        "href_equipo": _ruta("evaluaciones:equipo", "/evaluaciones/equipo/"),
    }
    if user is None or empresa is None or ciclo is None:
        return vacio
    qs = (
        Evaluacion.objects.for_empresa(empresa)
        .filter(ciclo=ciclo, evaluador=user)
        .select_related("evaluado", "ciclo")
        .prefetch_related("respuestas")
    )
    total = qs.count()
    auto_hechas = qs.filter(estado__in=ESTADOS_AUTO).count()
    alertas = list(qs.filter(estado__in=ESTADOS_SIN_AUTO))
    vacio.update(
        {
            "evaluaciones": list(qs),
            "total": total,
            "auto_hechas": auto_hechas,
            "completitud": round((auto_hechas / total) * 100) if total else 0,
            "alertas_sin_auto": alertas,
        }
    )
    return vacio
