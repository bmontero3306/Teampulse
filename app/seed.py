"""Datos demo para UAT (WP10). Idempotente: no explota si ya hay datos."""

from datetime import date, timedelta
from decimal import Decimal

from cuentas.models import Usuario
from empresas.models import Empresa
from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaCriterio,
    PlantillaEvaluacion,
    PlantillaPuesto,
)
from evaluaciones.services import (
    activar_ciclo,
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
)
from organizacion.models import Area, Competencia, Puesto, PuestoCompetencia

DEMO_PASSWORD = "ClaveDemo-2026"

SUPERADMIN_EMAIL = "admin@teampulse.local"

EMPRESA_A_CUIT = "30708999991"
EMPRESA_B_CUIT = "30708999992"

EMAIL_RRHH_A = "rrhh@acme.local"
EMAIL_SUPERVISOR = "supervisor@acme.local"
EMAIL_EMPLEADO_1 = "empleado1@acme.local"
EMAIL_EMPLEADO_2 = "empleado2@acme.local"
EMAIL_EMPLEADO_3 = "empleado3@acme.local"
EMAIL_RRHH_B = "rrhh@beta.local"

CUENTAS_DEMO = (
    (SUPERADMIN_EMAIL, "superadmin", "Plataforma"),
    (EMAIL_RRHH_A, "admin_rrhh", "Acme"),
    (EMAIL_SUPERVISOR, "supervisor", "Acme"),
    (EMAIL_EMPLEADO_1, "empleado", "Acme · pendiente de autoevaluación"),
    (EMAIL_EMPLEADO_2, "empleado", "Acme · autoevaluación enviada"),
    (EMAIL_EMPLEADO_3, "empleado", "Acme · evaluación cerrada"),
    (EMAIL_RRHH_B, "admin_rrhh", "Beta · aislamiento tenant"),
)


def _escribir(stdout, mensaje):
    if stdout is not None:
        stdout.write(mensaje)


def _upsert_empresa(cuit, **campos):
    empresa = Empresa.objects.filter(cuit=cuit).first()
    if empresa is None:
        return Empresa.objects.create(cuit=cuit, **campos), True
    for clave, valor in campos.items():
        setattr(empresa, clave, valor)
    empresa.save()
    return empresa, False


def _upsert_usuario(email, empresa, password, **campos):
    qs = Usuario.objects.filter(email__iexact=email)
    if empresa is None:
        qs = qs.filter(empresa__isnull=True)
    else:
        qs = qs.filter(empresa=empresa)
    usuario = qs.first()
    campos = dict(campos)
    campos["must_change_password"] = False
    campos["is_active"] = True
    campos["bloqueado"] = False
    if usuario is None:
        rol = campos.pop("rol", Usuario.Rol.EMPLEADO)
        extra = {"rol": rol, **campos}
        if empresa is None or rol == Usuario.Rol.SUPERADMIN:
            usuario = Usuario.objects.create_superuser(
                email=email,
                password=password,
                **extra,
            )
        else:
            usuario = Usuario.objects.create_user(
                email=email,
                password=password,
                empresa=empresa,
                **extra,
            )
        return usuario, True
    for clave, valor in campos.items():
        setattr(usuario, clave, valor)
    if empresa is not None:
        usuario.empresa = empresa
    usuario.set_password(password)
    usuario.save()
    return usuario, False


def _upsert_named(model, empresa, nombre, **campos):
    obj = model.objects.filter(empresa=empresa, nombre=nombre).first()
    if obj is None:
        return model.objects.create(empresa=empresa, nombre=nombre, **campos), True
    for clave, valor in campos.items():
        setattr(obj, clave, valor)
    obj.save()
    return obj, False


def _respuestas(evaluacion, campo_puntaje, campo_comentario, puntaje, comentario):
    return {
        item.pk: {campo_puntaje: puntaje, campo_comentario: comentario}
        for item in evaluacion.respuestas.all()
    }


def _avanzar_auto(evaluacion, usuario, enviar, puntaje=4):
    evaluacion.refresh_from_db()
    if evaluacion.estado not in (
        Evaluacion.Estado.PENDIENTE_AUTO,
        Evaluacion.Estado.AUTO_BORRADOR,
    ):
        return evaluacion
    return guardar_autoevaluacion(
        evaluacion,
        _respuestas(
            evaluacion,
            "puntaje_empleado",
            "comentario_empleado",
            puntaje,
            "Comentario demo de autoevaluación.",
        ),
        enviar,
        usuario,
    )


def _avanzar_supervisor(evaluacion, supervisor, cerrar, puntaje=5):
    evaluacion.refresh_from_db()
    if evaluacion.estado not in (
        Evaluacion.Estado.AUTO_COMPLETA,
        Evaluacion.Estado.SUPERVISOR_BORRADOR,
    ):
        return evaluacion
    return guardar_eval_supervisor(
        evaluacion,
        _respuestas(
            evaluacion,
            "puntaje_supervisor",
            "comentario_supervisor",
            puntaje,
            "Comentario demo del supervisor.",
        ),
        "Feedback demo: buen desempeño en el ciclo.",
        cerrar,
        supervisor,
    )


def seed_demo(stdout=None):
    """Crea o actualiza el escenario demo. Devuelve un dict con las entidades."""
    empresa_a, _ = _upsert_empresa(
        EMPRESA_A_CUIT,
        nombre="Acme Demo",
        razon_social="Acme Demo S.A.",
        email_contacto="contacto@acme.local",
        telefono="011-4000-1000",
        direccion="Av. Corrientes 1234, CABA",
        estado=Empresa.Estado.ACTIVA,
    )
    empresa_b, _ = _upsert_empresa(
        EMPRESA_B_CUIT,
        nombre="Beta Demo",
        razon_social="Beta Demo S.A.",
        email_contacto="contacto@beta.local",
        telefono="011-4000-2000",
        direccion="Av. Santa Fe 5678, CABA",
        estado=Empresa.Estado.ACTIVA,
    )

    superadmin, _ = _upsert_usuario(
        SUPERADMIN_EMAIL,
        None,
        DEMO_PASSWORD,
        rol=Usuario.Rol.SUPERADMIN,
        first_name="Super",
        last_name="Admin",
        is_staff=True,
        is_superuser=True,
    )

    area, _ = _upsert_named(Area, empresa_a, "Operaciones", activa=True)
    puesto_jefe, _ = _upsert_named(
        Puesto,
        empresa_a,
        "Jefe de equipo",
        descripcion="Coordina al equipo de analistas.",
        area=area,
        puesto_superior=None,
        activo=True,
    )
    puesto_analista, _ = _upsert_named(
        Puesto,
        empresa_a,
        "Analista",
        descripcion="Puesto de analista de operaciones.",
        area=area,
        puesto_superior=puesto_jefe,
        activo=True,
    )

    comp_tec, _ = _upsert_named(
        Competencia,
        empresa_a,
        "Conocimiento técnico",
        descripcion="Dominio de herramientas y procesos.",
        tipo=Competencia.Tipo.TECNICA,
        activa=True,
    )
    comp_act, _ = _upsert_named(
        Competencia,
        empresa_a,
        "Trabajo en equipo",
        descripcion="Colaboración y comunicación.",
        tipo=Competencia.Tipo.ACTITUDINAL,
        activa=True,
    )
    for puesto, competencia, ponderacion in (
        (puesto_jefe, comp_tec, Decimal("50")),
        (puesto_jefe, comp_act, Decimal("50")),
        (puesto_analista, comp_tec, Decimal("50")),
        (puesto_analista, comp_act, Decimal("50")),
    ):
        PuestoCompetencia.objects.get_or_create(
            puesto=puesto,
            competencia=competencia,
            defaults={"ponderacion": ponderacion},
        )

    admin_a, _ = _upsert_usuario(
        EMAIL_RRHH_A,
        empresa_a,
        DEMO_PASSWORD,
        rol=Usuario.Rol.ADMIN_RRHH,
        first_name="Rita",
        last_name="RRHH",
        area=area,
    )
    supervisor, _ = _upsert_usuario(
        EMAIL_SUPERVISOR,
        empresa_a,
        DEMO_PASSWORD,
        rol=Usuario.Rol.SUPERVISOR,
        first_name="Diego",
        last_name="López",
        area=area,
        puesto=puesto_jefe,
        supervisor=None,
    )
    empleado_1, _ = _upsert_usuario(
        EMAIL_EMPLEADO_1,
        empresa_a,
        DEMO_PASSWORD,
        rol=Usuario.Rol.EMPLEADO,
        first_name="Ana",
        last_name="Pérez",
        area=area,
        puesto=puesto_analista,
        supervisor=supervisor,
    )
    empleado_2, _ = _upsert_usuario(
        EMAIL_EMPLEADO_2,
        empresa_a,
        DEMO_PASSWORD,
        rol=Usuario.Rol.EMPLEADO,
        first_name="Bruno",
        last_name="Gómez",
        area=area,
        puesto=puesto_analista,
        supervisor=supervisor,
    )
    empleado_3, _ = _upsert_usuario(
        EMAIL_EMPLEADO_3,
        empresa_a,
        DEMO_PASSWORD,
        rol=Usuario.Rol.EMPLEADO,
        first_name="Carla",
        last_name="Ruiz",
        area=area,
        puesto=puesto_analista,
        supervisor=supervisor,
    )
    admin_b, _ = _upsert_usuario(
        EMAIL_RRHH_B,
        empresa_b,
        DEMO_PASSWORD,
        rol=Usuario.Rol.ADMIN_RRHH,
        first_name="Bárbara",
        last_name="Beta",
    )

    plantilla, _ = _upsert_named(
        PlantillaEvaluacion,
        empresa_a,
        "Plantilla mixta anual",
        tipo=PlantillaEvaluacion.Tipo.MIXTA,
        descripcion="Técnica y actitudinal para el ciclo demo.",
        activa=True,
    )
    for orden, competencia in ((1, comp_tec), (2, comp_act)):
        PlantillaCriterio.objects.get_or_create(
            plantilla=plantilla,
            competencia=competencia,
            defaults={
                "orden": orden,
                "escala_min": 1,
                "escala_max": 5,
                "ponderacion": Decimal("50"),
                "comentario_empleado_obligatorio": False,
                "comentario_supervisor_obligatorio": False,
            },
        )
    for puesto in (puesto_jefe, puesto_analista):
        PlantillaPuesto.objects.get_or_create(plantilla=plantilla, puesto=puesto)

    ciclo = CicloEvaluacion.objects.filter(
        empresa=empresa_a, nombre="Ciclo demo 2026"
    ).first()
    if ciclo is None:
        ciclo = CicloEvaluacion.objects.create(
            empresa=empresa_a,
            nombre="Ciclo demo 2026",
            fecha_inicio=date.today(),
            fecha_cierre=date.today() + timedelta(days=30),
            estado=CicloEvaluacion.Estado.BORRADOR,
            plantilla_default=plantilla,
            criterios_generales="Completar con honestidad. Escala 1 a 5.",
        )
    else:
        ciclo.plantilla_default = plantilla
        ciclo.fecha_inicio = ciclo.fecha_inicio or date.today()
        ciclo.fecha_cierre = ciclo.fecha_cierre or (date.today() + timedelta(days=30))
        ciclo.save()

    if ciclo.estado == CicloEvaluacion.Estado.BORRADOR:
        ciclo, _sin = activar_ciclo(ciclo, admin_a)
        _escribir(stdout, "Ciclo demo activado.")
    elif ciclo.estado != CicloEvaluacion.Estado.ACTIVO:
        _escribir(
            stdout,
            f"El ciclo demo está en estado «{ciclo.estado}»; no se reactivó.",
        )

    evals = {
        ev.evaluado_id: ev
        for ev in Evaluacion.objects.filter(ciclo=ciclo).select_related("evaluado")
    }
    ev1 = evals.get(empleado_1.pk)
    ev2 = evals.get(empleado_2.pk)
    ev3 = evals.get(empleado_3.pk)
    ev_sup = evals.get(supervisor.pk)

    if ev2 is not None:
        _avanzar_auto(ev2, empleado_2, enviar=True)
    if ev3 is not None:
        _avanzar_auto(ev3, empleado_3, enviar=True)
        _avanzar_supervisor(ev3, supervisor, cerrar=True)
        ev3.refresh_from_db()
        if ev3.estado == Evaluacion.Estado.PENDIENTE_CONFORMIDAD:
            firmar_conformidad(ev3, empleado_3, "127.0.0.1")
    if ev_sup is not None:
        _avanzar_auto(ev_sup, supervisor, enviar=False, puntaje=3)

    resultado = {
        "empresa_a": empresa_a,
        "empresa_b": empresa_b,
        "superadmin": superadmin,
        "admin_a": admin_a,
        "supervisor": supervisor,
        "empleado_1": empleado_1,
        "empleado_2": empleado_2,
        "empleado_3": empleado_3,
        "admin_b": admin_b,
        "ciclo": ciclo,
        "plantilla": plantilla,
        "evaluacion_pendiente": ev1,
        "evaluacion_auto_completa": ev2,
        "evaluacion_cerrada": ev3,
        "evaluacion_supervisor": ev_sup,
        "password": DEMO_PASSWORD,
    }
    _escribir(stdout, "Datos demo listos. Contraseña de todas las cuentas: " + DEMO_PASSWORD)
    return resultado
