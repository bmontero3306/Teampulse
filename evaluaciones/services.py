import hashlib

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.models import (
    CicloEvaluacion,
    Evaluacion,
    PlantillaCriterio,
    PlantillaEvaluacion,
    PlantillaPuesto,
    RespuestaItem,
)
from notificaciones.events import (
    AUTOEVALUACION_ENVIADA,
    CICLO_ACTIVADO,
    CICLO_CANCELADO,
    CICLO_PAUSADO,
    CICLO_REPROGRAMADO,
    CONFORMIDAD_FIRMADA,
    CONFORMIDAD_OBSERVACION,
    EVALUACION_SUPERVISOR_CERRADA,
)
from notificaciones.services import notificar


@transaction.atomic
def duplicar_plantilla(plantilla):
    """Copia nombre «Copia de …», criterios y puestos. No comparte PK."""
    nueva = PlantillaEvaluacion.objects.create(
        empresa=plantilla.empresa,
        nombre=f"Copia de {plantilla.nombre}",
        tipo=plantilla.tipo,
        descripcion=plantilla.descripcion,
        activa=plantilla.activa,
        duplicada_desde=plantilla,
    )
    for criterio in plantilla.criterios.all():
        PlantillaCriterio.objects.create(
            plantilla=nueva,
            competencia=criterio.competencia,
            orden=criterio.orden,
            escala_min=criterio.escala_min,
            escala_max=criterio.escala_max,
            ponderacion=criterio.ponderacion,
            comentario_empleado_obligatorio=criterio.comentario_empleado_obligatorio,
            comentario_supervisor_obligatorio=criterio.comentario_supervisor_obligatorio,
        )
    for vinculo in plantilla.plantilla_puestos.all():
        PlantillaPuesto.objects.create(plantilla=nueva, puesto=vinculo.puesto)
    return nueva


def resolver_evaluador(usuario):
    """Prioriza usuario.supervisor; si no hay, el ocupante de puesto_superior."""
    supervisor = getattr(usuario, "supervisor", None)
    if (
        supervisor is not None
        and supervisor.pk != getattr(usuario, "pk", None)
        and supervisor.is_active
        and not supervisor.bloqueado
    ):
        return supervisor

    puesto = getattr(usuario, "puesto", None)
    if puesto is None:
        return None
    puesto_superior_id = getattr(puesto, "puesto_superior_id", None)
    if not puesto_superior_id:
        return None

    ocupantes = Usuario.objects.filter(
        puesto_id=puesto_superior_id,
        is_active=True,
        bloqueado=False,
        empresa_id=usuario.empresa_id,
    )
    pk = getattr(usuario, "pk", None)
    if pk:
        ocupantes = ocupantes.exclude(pk=pk)
    return ocupantes.first()


def resolver_plantilla(usuario, ciclo):
    puesto = getattr(usuario, "puesto", None)
    if puesto is not None:
        vinculo = (
            PlantillaPuesto.objects.filter(
                puesto=puesto,
                plantilla__empresa=ciclo.empresa,
                plantilla__activa=True,
            )
            .select_related("plantilla")
            .first()
        )
        if vinculo is not None:
            return vinculo.plantilla
    return ciclo.plantilla_default


def _usuarios_participantes(ciclo):
    qs = Usuario.objects.filter(
        empresa=ciclo.empresa,
        is_active=True,
        bloqueado=False,
        puesto__isnull=False,
    ).select_related("puesto", "puesto__puesto_superior", "supervisor", "area")
    areas_ids = list(ciclo.areas.values_list("pk", flat=True))
    if areas_ids:
        qs = qs.filter(area_id__in=areas_ids)
    return qs


def _contexto_ciclo(ciclo, url=""):
    fecha = ""
    if ciclo.fecha_cierre:
        fecha = ciclo.fecha_cierre.strftime("%d/%m/%Y")
    return {
        "ciclo": ciclo.nombre,
        "fecha_cierre": fecha,
        "url": url,
        "nombre": "",
        "empresa": str(ciclo.empresa),
        "evaluado": "",
    }


def _notificar_participantes(ciclo, tipo, url=""):
    contexto = _contexto_ciclo(ciclo, url=url)
    vistos = set()
    for evaluacion in ciclo.evaluaciones.select_related("evaluado", "evaluador"):
        for usuario in (evaluacion.evaluado, evaluacion.evaluador):
            if usuario is None or usuario.pk in vistos:
                continue
            vistos.add(usuario.pk)
            notificar(
                tipo=tipo,
                usuario=usuario,
                empresa=ciclo.empresa,
                contexto=contexto,
            )


def _admins_rrhh(empresa):
    return Usuario.objects.filter(
        empresa=empresa,
        rol=Usuario.Rol.ADMIN_RRHH,
        is_active=True,
        bloqueado=False,
    )


def calcular_firma_hash(evaluacion_id, user_id, timestamp, puntajes):
    """sha256 de evaluacion_id|user_id|timestamp|puntajes. Determinístico."""
    ts = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
    puntajes_str = ",".join("" if p is None else str(p) for p in puntajes)
    payload = f"{evaluacion_id}|{user_id}|{ts}|{puntajes_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _asegurar_ciclo_editable(ciclo):
    if ciclo.estado == CicloEvaluacion.Estado.CANCELADO:
        raise EvaluacionesError(
            "El ciclo está cancelado. No se pueden realizar más ediciones."
        )
    if ciclo.estado == CicloEvaluacion.Estado.CERRADO:
        raise EvaluacionesError(
            "El ciclo está cerrado. No se pueden realizar más ediciones."
        )
    if ciclo.estado == CicloEvaluacion.Estado.PAUSADO:
        raise EvaluacionesError(
            "El ciclo está pausado. No se pueden editar evaluaciones."
        )
    if ciclo.estado != CicloEvaluacion.Estado.ACTIVO:
        raise EvaluacionesError("El ciclo no está activo.")


def _puntajes_en_rango(criterio, puntaje, etiqueta):
    if puntaje is None:
        return
    if puntaje < criterio.escala_min or puntaje > criterio.escala_max:
        raise EvaluacionesError(
            f"El {etiqueta} de «{criterio.competencia}» debe estar entre "
            f"{criterio.escala_min} y {criterio.escala_max}."
        )


@transaction.atomic
def asignar_evaluaciones_ciclo(ciclo):
    """Crea Evaluacion + RespuestaItem vacíos. Idempotente por (ciclo, evaluado)."""
    creadas = []
    sin_evaluador = []
    for usuario in _usuarios_participantes(ciclo):
        puesto = usuario.puesto
        if puesto is None:
            continue
        plantilla = resolver_plantilla(usuario, ciclo)
        evaluador = resolver_evaluador(usuario)
        sin_eval = evaluador is None
        evaluacion, created = Evaluacion.objects.get_or_create(
            ciclo=ciclo,
            evaluado=usuario,
            defaults={
                "empresa": ciclo.empresa,
                "evaluador": evaluador,
                "puesto": puesto,
                "plantilla": plantilla,
                "estado": Evaluacion.Estado.PENDIENTE_AUTO,
                "sin_evaluador": sin_eval,
            },
        )
        if created:
            criterios = PlantillaCriterio.objects.filter(plantilla=plantilla)
            RespuestaItem.objects.bulk_create(
                [
                    RespuestaItem(evaluacion=evaluacion, criterio=criterio)
                    for criterio in criterios
                ]
            )
            creadas.append(evaluacion)
            if sin_eval:
                sin_evaluador.append(evaluacion)
        elif evaluacion.sin_evaluador:
            sin_evaluador.append(evaluacion)
    return creadas, sin_evaluador


@transaction.atomic
def activar_ciclo(ciclo, usuario, request=None):
    if ciclo.estado in (
        CicloEvaluacion.Estado.CANCELADO,
        CicloEvaluacion.Estado.CERRADO,
    ):
        raise EvaluacionesError("No se puede activar un ciclo cancelado o cerrado.")
    if ciclo.estado == CicloEvaluacion.Estado.ACTIVO:
        raise EvaluacionesError("El ciclo ya está activo.")

    otro_activo = (
        CicloEvaluacion.objects.filter(
            empresa=ciclo.empresa,
            estado=CicloEvaluacion.Estado.ACTIVO,
        )
        .exclude(pk=ciclo.pk)
        .exists()
    )
    if otro_activo:
        raise EvaluacionesError("Ya hay un ciclo activo en esta empresa.")

    era_borrador = ciclo.estado == CicloEvaluacion.Estado.BORRADOR
    if era_borrador:
        participantes = _usuarios_participantes(ciclo)
        if not participantes.exists():
            raise EvaluacionesError("No hay empleados con puesto asignado.")

    ciclo.estado = CicloEvaluacion.Estado.ACTIVO
    if ciclo.activado_en is None:
        ciclo.activado_en = timezone.now()
        ciclo.activado_por = usuario
        ciclo.save(
            update_fields=["estado", "activado_en", "activado_por"]
        )
    else:
        ciclo.save(update_fields=["estado"])

    sin_evaluador = []
    if era_borrador:
        _creadas, sin_evaluador = asignar_evaluaciones_ciclo(ciclo)

    registrar_auditoria(
        request,
        accion="activar",
        instance=ciclo,
        usuario=usuario,
        payload={"estado": ciclo.estado, "sin_evaluador": len(sin_evaluador)},
    )
    url_mias = reverse("evaluaciones:mias")
    _notificar_participantes(ciclo, CICLO_ACTIVADO, url=url_mias)
    return ciclo, sin_evaluador


@transaction.atomic
def pausar_ciclo(ciclo, usuario, request=None):
    if ciclo.estado != CicloEvaluacion.Estado.ACTIVO:
        raise EvaluacionesError("Solo se puede pausar un ciclo activo.")
    ciclo.estado = CicloEvaluacion.Estado.PAUSADO
    ciclo.save(update_fields=["estado"])
    registrar_auditoria(request, accion="pausar", instance=ciclo, usuario=usuario)
    _notificar_participantes(ciclo, CICLO_PAUSADO, url=reverse("evaluaciones:mias"))
    return ciclo


@transaction.atomic
def cancelar_ciclo(ciclo, usuario, request=None):
    if ciclo.estado in (
        CicloEvaluacion.Estado.CANCELADO,
        CicloEvaluacion.Estado.CERRADO,
    ):
        raise EvaluacionesError("El ciclo ya está cancelado o cerrado.")
    ciclo.estado = CicloEvaluacion.Estado.CANCELADO
    ciclo.save(update_fields=["estado"])
    registrar_auditoria(request, accion="cancelar", instance=ciclo, usuario=usuario)
    _notificar_participantes(ciclo, CICLO_CANCELADO, url=reverse("evaluaciones:mias"))
    return ciclo


@transaction.atomic
def reprogramar_ciclo(ciclo, fecha_inicio, fecha_cierre, usuario, request=None):
    if ciclo.estado in (
        CicloEvaluacion.Estado.CANCELADO,
        CicloEvaluacion.Estado.CERRADO,
    ):
        raise EvaluacionesError("No se puede reprogramar un ciclo cancelado o cerrado.")
    if fecha_cierre < fecha_inicio:
        raise EvaluacionesError("La fecha de cierre no puede ser anterior al inicio.")
    ciclo.fecha_inicio = fecha_inicio
    ciclo.fecha_cierre = fecha_cierre
    ciclo.save(update_fields=["fecha_inicio", "fecha_cierre"])
    registrar_auditoria(
        request,
        accion="reprogramar",
        instance=ciclo,
        usuario=usuario,
        payload={
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_cierre": fecha_cierre.isoformat(),
        },
    )
    _notificar_participantes(
        ciclo, CICLO_REPROGRAMADO, url=reverse("evaluaciones:mias")
    )
    return ciclo


def _items_por_id(evaluacion):
    return {
        item.pk: item
        for item in evaluacion.respuestas.select_related(
            "criterio", "criterio__competencia"
        )
    }


@transaction.atomic
def guardar_autoevaluacion(evaluacion, respuestas, enviar, usuario, request=None):
    """respuestas: dict {respuesta_id: {puntaje_empleado, comentario_empleado}}."""
    _asegurar_ciclo_editable(evaluacion.ciclo)
    if evaluacion.evaluado_id != getattr(usuario, "pk", None):
        raise EvaluacionesError("Solo el evaluado puede completar la autoevaluación.")
    if evaluacion.estado not in (
        Evaluacion.Estado.PENDIENTE_AUTO,
        Evaluacion.Estado.AUTO_BORRADOR,
    ):
        raise EvaluacionesError(
            "No podés editar la autoevaluación después de enviarla."
        )

    items = _items_por_id(evaluacion)
    for item_id, datos in respuestas.items():
        item = items.get(item_id)
        if item is None:
            raise EvaluacionesError("Hay ítems que no pertenecen a esta evaluación.")
        puntaje = datos.get("puntaje_empleado")
        comentario = (datos.get("comentario_empleado") or "").strip()
        _puntajes_en_rango(item.criterio, puntaje, "puntaje del empleado")
        item.puntaje_empleado = puntaje
        item.comentario_empleado = comentario

    if enviar:
        for item in items.values():
            if item.puntaje_empleado is None:
                raise EvaluacionesError(
                    f"Falta el puntaje de «{item.criterio.competencia}»."
                )
            if (
                item.criterio.comentario_empleado_obligatorio
                and not (item.comentario_empleado or "").strip()
            ):
                raise EvaluacionesError(
                    f"El comentario del empleado es obligatorio en «{item.criterio.competencia}»."
                )
        evaluacion.estado = Evaluacion.Estado.AUTO_COMPLETA
        evaluacion.enviada_auto_en = timezone.now()
        evaluacion.save(update_fields=["estado", "enviada_auto_en"])
    else:
        evaluacion.estado = Evaluacion.Estado.AUTO_BORRADOR
        evaluacion.save(update_fields=["estado"])

    RespuestaItem.objects.bulk_update(
        list(items.values()),
        ["puntaje_empleado", "comentario_empleado"],
    )

    registrar_auditoria(
        request,
        accion="enviar_autoevaluacion" if enviar else "guardar_autoevaluacion",
        instance=evaluacion,
        usuario=usuario,
        payload={"estado": evaluacion.estado},
    )
    if enviar and evaluacion.evaluador_id:
        notificar(
            tipo=AUTOEVALUACION_ENVIADA,
            usuario=evaluacion.evaluador,
            empresa=evaluacion.empresa,
            contexto={
                "ciclo": evaluacion.ciclo.nombre,
                "evaluado": evaluacion.evaluado.get_full_name()
                or evaluacion.evaluado.email,
                "url": reverse("evaluaciones:supervisar", args=[evaluacion.pk]),
            },
        )
    return evaluacion


@transaction.atomic
def guardar_eval_supervisor(
    evaluacion, respuestas, feedback_supervisor, cerrar, usuario, request=None
):
    """respuestas: dict {respuesta_id: {puntaje_supervisor, comentario_supervisor}}."""
    _asegurar_ciclo_editable(evaluacion.ciclo)
    if evaluacion.evaluador_id != getattr(usuario, "pk", None):
        raise EvaluacionesError(
            "Solo el evaluador asignado puede completar esta evaluación."
        )
    if evaluacion.estado in (
        Evaluacion.Estado.PENDIENTE_AUTO,
        Evaluacion.Estado.AUTO_BORRADOR,
    ):
        raise EvaluacionesError(
            "El supervisor no puede evaluar antes de que se complete la autoevaluación."
        )
    if evaluacion.estado not in (
        Evaluacion.Estado.AUTO_COMPLETA,
        Evaluacion.Estado.SUPERVISOR_BORRADOR,
    ):
        raise EvaluacionesError("Esta evaluación ya no admite cambios del supervisor.")

    items = _items_por_id(evaluacion)
    for item_id, datos in respuestas.items():
        item = items.get(item_id)
        if item is None:
            raise EvaluacionesError("Hay ítems que no pertenecen a esta evaluación.")
        puntaje = datos.get("puntaje_supervisor")
        comentario = (datos.get("comentario_supervisor") or "").strip()
        _puntajes_en_rango(item.criterio, puntaje, "puntaje del supervisor")
        item.puntaje_supervisor = puntaje
        item.comentario_supervisor = comentario

    feedback = (feedback_supervisor or "").strip()
    evaluacion.feedback_supervisor = feedback

    if cerrar:
        if not feedback:
            raise EvaluacionesError(
                "El feedback del supervisor es obligatorio para cerrar."
            )
        for item in items.values():
            if item.puntaje_supervisor is None:
                raise EvaluacionesError(
                    f"Falta el puntaje de supervisor en «{item.criterio.competencia}»."
                )
            if (
                item.criterio.comentario_supervisor_obligatorio
                and not (item.comentario_supervisor or "").strip()
            ):
                raise EvaluacionesError(
                    f"El comentario del supervisor es obligatorio en «{item.criterio.competencia}»."
                )
        evaluacion.estado = Evaluacion.Estado.PENDIENTE_CONFORMIDAD
        evaluacion.cerrada_supervisor_en = timezone.now()
        evaluacion.save(
            update_fields=["estado", "feedback_supervisor", "cerrada_supervisor_en"]
        )
    else:
        evaluacion.estado = Evaluacion.Estado.SUPERVISOR_BORRADOR
        evaluacion.save(update_fields=["estado", "feedback_supervisor"])

    RespuestaItem.objects.bulk_update(
        list(items.values()),
        ["puntaje_supervisor", "comentario_supervisor"],
    )

    registrar_auditoria(
        request,
        accion="cerrar_supervisor" if cerrar else "guardar_supervisor",
        instance=evaluacion,
        usuario=usuario,
        payload={"estado": evaluacion.estado},
    )
    if cerrar:
        notificar(
            tipo=EVALUACION_SUPERVISOR_CERRADA,
            usuario=evaluacion.evaluado,
            empresa=evaluacion.empresa,
            contexto={
                "ciclo": evaluacion.ciclo.nombre,
                "evaluado": evaluacion.evaluado.get_full_name()
                or evaluacion.evaluado.email,
                "url": reverse("evaluaciones:resultado", args=[evaluacion.pk]),
            },
        )
    return evaluacion


@transaction.atomic
def firmar_conformidad(evaluacion, user, ip, observacion=None):
    _asegurar_ciclo_editable(evaluacion.ciclo)
    if evaluacion.evaluado_id != getattr(user, "pk", None):
        raise EvaluacionesError("Solo el evaluado puede firmar esta evaluación.")
    if evaluacion.estado != Evaluacion.Estado.PENDIENTE_CONFORMIDAD:
        raise EvaluacionesError("La evaluación no está pendiente de conformidad.")
    if evaluacion.esta_cerrada:
        raise EvaluacionesError("La evaluación ya está cerrada.")

    observacion = (observacion or "").strip() or None
    ahora = timezone.now()
    puntajes = list(
        evaluacion.respuestas.order_by("criterio__orden", "criterio_id").values_list(
            "puntaje_supervisor", flat=True
        )
    )
    evaluacion.firmada_en = ahora
    evaluacion.ip_firma = ip
    evaluacion.firma_hash = calcular_firma_hash(
        evaluacion.pk, user.pk, ahora, puntajes
    )
    if observacion:
        evaluacion.estado = Evaluacion.Estado.CERRADA_CON_OBS
        evaluacion.comentario_empleado_cierre = observacion
        tipo = CONFORMIDAD_OBSERVACION
        accion = "observar_conformidad"
    else:
        evaluacion.estado = Evaluacion.Estado.CERRADA
        tipo = CONFORMIDAD_FIRMADA
        accion = "firmar_conformidad"
    campos = ["estado", "firmada_en", "ip_firma", "firma_hash"]
    if observacion:
        campos.append("comentario_empleado_cierre")
    evaluacion.save(update_fields=campos)

    registrar_auditoria(
        None,
        accion=accion,
        instance=evaluacion,
        usuario=user,
        ip=ip,
        payload={
            "estado": evaluacion.estado,
            "firma_hash": evaluacion.firma_hash,
        },
    )
    contexto = {
        "ciclo": evaluacion.ciclo.nombre,
        "evaluado": evaluacion.evaluado.get_full_name() or evaluacion.evaluado.email,
        "url": reverse("evaluaciones:resultado", args=[evaluacion.pk]),
    }
    destinatarios = []
    if evaluacion.evaluador_id:
        destinatarios.append(evaluacion.evaluador)
    destinatarios.extend(_admins_rrhh(evaluacion.empresa))
    vistos = set()
    for dest in destinatarios:
        if dest is None or dest.pk in vistos:
            continue
        vistos.add(dest.pk)
        notificar(
            tipo=tipo,
            usuario=dest,
            empresa=evaluacion.empresa,
            contexto=contexto,
        )
    return evaluacion
