"""Helpers de fixtures para tests de reportes ISO (WP7)."""

from datetime import timedelta

from django.utils import timezone

from app.tests.factories import (
    make_area,
    make_ciclo,
    make_empresa,
    make_evaluacion,
    make_plantilla,
    make_puesto,
    make_usuario,
)
from evaluaciones.models import Evaluacion


def escenario_iso_basico():
    """Empresa, ciclo, área y evaluaciones en distintos estados."""
    empresa = make_empresa()
    area = make_area(empresa)
    puesto = make_puesto(empresa, area=area)
    plantilla = make_plantilla(empresa)
    ciclo = make_ciclo(empresa, plantilla_default=plantilla)
    ciclo.activado_en = timezone.now() - timedelta(days=20)
    ciclo.save(update_fields=["activado_en"])

    admin = make_usuario(empresa, rol="admin_rrhh", first_name="Ana", last_name="RRHH")
    supervisor = make_usuario(
        empresa,
        rol="supervisor",
        puesto=puesto,
        area=area,
        first_name="Sara",
        last_name="Jefa",
    )
    empleado = make_usuario(
        empresa,
        rol="empleado",
        puesto=puesto,
        area=area,
        supervisor=supervisor,
        first_name="Pablo",
        last_name="Evaluado",
    )
    empleado_b = make_usuario(
        empresa,
        rol="empleado",
        puesto=puesto,
        area=area,
        supervisor=supervisor,
        first_name="Marta",
        last_name="Pendiente",
    )

    firmada = make_evaluacion(
        ciclo,
        empleado,
        evaluador=supervisor,
        puesto=puesto,
        estado=Evaluacion.Estado.CERRADA,
        enviada_auto_en=timezone.now() - timedelta(days=10),
        cerrada_supervisor_en=timezone.now() - timedelta(days=5),
        firmada_en=timezone.now() - timedelta(days=1),
        firma_hash="a" * 64,
    )
    pendiente = make_evaluacion(
        ciclo,
        empleado_b,
        evaluador=supervisor,
        puesto=puesto,
        estado=Evaluacion.Estado.PENDIENTE_AUTO,
    )
    return {
        "empresa": empresa,
        "area": area,
        "puesto": puesto,
        "ciclo": ciclo,
        "admin": admin,
        "supervisor": supervisor,
        "empleado": empleado,
        "empleado_b": empleado_b,
        "firmada": firmada,
        "pendiente": pendiente,
    }
