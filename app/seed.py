"""Datos demo para UAT (WP10). Idempotente: no explota si ya hay datos."""

import random
import re
import unicodedata
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
    RespuestaItem,
)
from evaluaciones.services import (
    activar_ciclo,
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
    resolver_plantilla,
)
from organizacion.models import Area, Competencia, Puesto

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


def _renombrar_si_existe(model, empresa, nombre_viejo, nombre_nuevo):
    """Evita duplicar el organigrama legado al re-ejecutar el seed."""
    if model.objects.filter(empresa=empresa, nombre=nombre_nuevo).exists():
        return
    obj = model.objects.filter(empresa=empresa, nombre=nombre_viejo).first()
    if obj is not None:
        obj.nombre = nombre_nuevo
        obj.save(update_fields=["nombre"])


def _upsert_area(empresa, nombre, area_padre=None):
    area, _ = _upsert_named(
        Area, empresa, nombre, area_padre=area_padre, activa=True
    )
    return area


def _upsert_puesto(empresa, nombre, *, area, puesto_superior=None, descripcion=""):
    puesto, _ = _upsert_named(
        Puesto,
        empresa,
        nombre,
        descripcion=descripcion,
        area=area,
        puesto_superior=puesto_superior,
        activo=True,
    )
    return puesto


def _seed_organigrama(empresa):
    """Áreas y puestos del organigrama (sin las personas que ocupan cada caja)."""
    _renombrar_si_existe(Area, empresa, "Operaciones", "Recursos Humanos")
    _renombrar_si_existe(Puesto, empresa, "Jefe de equipo", "Gerente de RRHH")
    _renombrar_si_existe(Puesto, empresa, "Analista", "Analistas RRHH")

    direccion = _upsert_area(empresa, "Dirección General")
    consultoria = _upsert_area(empresa, "Consultoría Externa", direccion)
    transporte = _upsert_area(empresa, "Transporte y Logística", direccion)
    obras = _upsert_area(empresa, "Obras y Sustentabilidad", direccion)
    servicios = _upsert_area(empresa, "Servicios Empresariales", direccion)
    admin_fin = _upsert_area(empresa, "Administración y Finanzas", direccion)
    rrhh = _upsert_area(empresa, "Recursos Humanos", direccion)
    comercial = _upsert_area(empresa, "Comercial", direccion)
    taller = _upsert_area(empresa, "Taller y Mantenimiento de Flota", direccion)
    sistemas = _upsert_area(empresa, "Sistemas", direccion)

    presidente = _upsert_puesto(empresa, "Presidente y CEO", area=direccion)
    vice = _upsert_puesto(
        empresa, "Vicepresidente", area=direccion, puesto_superior=presidente
    )
    gerente_gral = _upsert_puesto(
        empresa, "Gerente General", area=direccion, puesto_superior=vice
    )
    _upsert_puesto(
        empresa,
        "Consultoría Externa",
        area=consultoria,
        puesto_superior=gerente_gral,
        descripcion="Asesoramiento en legales, seguridad e higiene y medicina laboral.",
    )

    ger_transporte = _upsert_puesto(
        empresa,
        "Gerencia de Transporte y Logística",
        area=transporte,
        puesto_superior=gerente_gral,
    )
    coord_log = _upsert_puesto(
        empresa,
        "Coordinador Logístico",
        area=transporte,
        puesto_superior=ger_transporte,
    )
    for nombre in (
        "Operación de Transporte",
        "Gestión y Control de Flota",
        "Gestión Documental",
        "Choferes",
    ):
        _upsert_puesto(empresa, nombre, area=transporte, puesto_superior=coord_log)

    ger_obras = _upsert_puesto(
        empresa,
        "Gerencia de Obras y Sustentabilidad",
        area=obras,
        puesto_superior=gerente_gral,
    )
    for nombre in (
        "Director de Obra",
        "Planificación de Proyectos",
        "Operación y Ejecución de Obras",
    ):
        _upsert_puesto(empresa, nombre, area=obras, puesto_superior=ger_obras)

    ger_serv = _upsert_puesto(
        empresa,
        "Gerencia de Servicios Empresariales",
        area=servicios,
        puesto_superior=gerente_gral,
    )
    for nombre in (
        "Operaciones de Servicios Empresariales",
        "Choferes / Conductores",
    ):
        _upsert_puesto(empresa, nombre, area=servicios, puesto_superior=ger_serv)

    ger_admin = _upsert_puesto(
        empresa,
        "Gerencia de Administración y Finanzas",
        area=admin_fin,
        puesto_superior=gerente_gral,
    )
    for nombre in ("Facturación y Cobranzas", "Compras", "Pagos", "Contable"):
        _upsert_puesto(empresa, nombre, area=admin_fin, puesto_superior=ger_admin)

    ger_rrhh = _upsert_puesto(
        empresa, "Gerente de RRHH", area=rrhh, puesto_superior=gerente_gral
    )
    analistas_rrhh = _upsert_puesto(
        empresa, "Analistas RRHH", area=rrhh, puesto_superior=ger_rrhh
    )

    _upsert_puesto(
        empresa, "Gerencia Comercial", area=comercial, puesto_superior=gerente_gral
    )

    ger_taller = _upsert_puesto(
        empresa,
        "Gerencia de Taller y Mantenimiento de Flota",
        area=taller,
        puesto_superior=gerente_gral,
    )
    jefe_taller = _upsert_puesto(
        empresa, "Jefe de Taller", area=taller, puesto_superior=ger_taller
    )
    sup_taller = _upsert_puesto(
        empresa, "Supervisor de Taller", area=taller, puesto_superior=jefe_taller
    )
    for nombre in ("Mecánicos", "Soldadura y Pintura", "Depósito de Herramientas"):
        _upsert_puesto(empresa, nombre, area=taller, puesto_superior=sup_taller)
    sup_playa = _upsert_puesto(
        empresa, "Supervisor de Playa", area=taller, puesto_superior=jefe_taller
    )
    for nombre in ("Mantenimiento Edilicio", "Seguridad"):
        _upsert_puesto(empresa, nombre, area=taller, puesto_superior=sup_playa)

    ger_sistemas = _upsert_puesto(
        empresa, "Gerencia de Sistemas", area=sistemas, puesto_superior=gerente_gral
    )
    _upsert_puesto(
        empresa,
        "Desarrollo de Software y Aplicaciones",
        area=sistemas,
        puesto_superior=ger_sistemas,
    )

    return {
        "area_rrhh": rrhh,
        "puesto_supervisor": ger_rrhh,
        "puesto_empleado": analistas_rrhh,
    }


NOMBRES_DEMO = (
    "Agustina",
    "Camila",
    "Daniel",
    "Elena",
    "Facundo",
    "Gonzalo",
    "Helena",
    "Iván",
    "Jimena",
    "Kevin",
    "Laura",
    "Matías",
    "Natalia",
    "Oscar",
    "Paula",
    "Ramiro",
    "Sofía",
    "Tomás",
    "Úrsula",
    "Valentina",
    "Walter",
    "Ximena",
    "Yamila",
    "Zoe",
    "Benjamín",
    "Celeste",
    "Damián",
    "Emilia",
    "Federico",
    "Gisela",
)

APELLIDOS_DEMO = (
    "Acosta",
    "Benítez",
    "Castro",
    "Domínguez",
    "Espósito",
    "Flores",
    "García",
    "Herrera",
    "Ibarra",
    "Juárez",
    "Kuznetsov",
    "Ledesma",
    "Molina",
    "Núñez",
    "Ortiz",
    "Paz",
    "Quiroga",
    "Ríos",
    "Sosa",
    "Torres",
    "Urrutia",
    "Vega",
    "Walsh",
    "Yáñez",
)

# Cupo por puesto: la mayoría 1; equipos operativos con 2 o 3 personas.
PUESTOS_CON_VARIOS = {
    "Analistas RRHH": 3,
    "Choferes": 3,
    "Choferes / Conductores": 3,
    "Mecánicos": 3,
    "Soldadura y Pintura": 2,
    "Operación de Transporte": 2,
    "Operación y Ejecución de Obras": 2,
    "Gestión Documental": 2,
    "Facturación y Cobranzas": 2,
    "Contable": 2,
    "Seguridad": 2,
    "Desarrollo de Software y Aplicaciones": 2,
}

_EMAILS_RESERVADOS = frozenset(
    email.lower()
    for email in (
        SUPERADMIN_EMAIL,
        EMAIL_RRHH_A,
        EMAIL_SUPERVISOR,
        EMAIL_EMPLEADO_1,
        EMAIL_EMPLEADO_2,
        EMAIL_EMPLEADO_3,
        EMAIL_RRHH_B,
    )
)


def _slug_email(texto):
    nfkd = unicodedata.normalize("NFKD", texto)
    ascii_txt = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", ".", ascii_txt.lower()).strip(".")


def _rol_para_puesto(puesto):
    if puesto.puestos_hijos.filter(activo=True).exists():
        return Usuario.Rol.SUPERVISOR
    nombre = puesto.nombre.casefold()
    if any(
        clave in nombre
        for clave in (
            "presidente",
            "vicepresidente",
            "gerente",
            "gerencia",
            "jefe",
            "supervisor",
            "director",
            "coordinador",
        )
    ):
        return Usuario.Rol.SUPERVISOR
    return Usuario.Rol.EMPLEADO


def _email_puesto(slug, indice):
    if indice == 1:
        return f"{slug}@acme.local"
    return f"{slug}.{indice}@acme.local"


def _seed_usuarios_puestos(empresa, password):
    """Cubre todos los puestos activos; en algunos deja 2 o 3 personas."""
    rng = random.Random(2026)
    puestos = list(
        Puesto.objects.filter(empresa=empresa, activo=True)
        .select_related("area", "puesto_superior")
        .order_by("pk")
    )
    ocupantes_por_puesto = {}
    usados = set(_EMAILS_RESERVADOS)

    for puesto in puestos:
        cupo = PUESTOS_CON_VARIOS.get(puesto.nombre, 1)
        ocupantes = list(
            Usuario.objects.filter(empresa=empresa, puesto=puesto, is_active=True).order_by("pk")
        )
        for ocupante in ocupantes:
            usados.add(ocupante.email.lower())
        slug = _slug_email(puesto.nombre) or "puesto"
        rol = _rol_para_puesto(puesto)
        indice = 1
        while len(ocupantes) < cupo:
            email = _email_puesto(slug, indice)
            indice += 1
            if email.lower() in usados:
                continue
            usados.add(email.lower())
            usuario, _ = _upsert_usuario(
                email,
                empresa,
                password,
                rol=rol,
                first_name=rng.choice(NOMBRES_DEMO),
                last_name=rng.choice(APELLIDOS_DEMO),
                dni=str(rng.randint(20_000_000, 45_999_999)),
                area=puesto.area,
                puesto=puesto,
            )
            ocupantes.append(usuario)
        ocupantes_por_puesto[puesto.pk] = ocupantes

    for puesto in puestos:
        jefe = None
        if puesto.puesto_superior_id:
            jefes = ocupantes_por_puesto.get(puesto.puesto_superior_id, [])
            jefe = jefes[0] if jefes else None
        for usuario in ocupantes_por_puesto.get(puesto.pk, []):
            nuevo_jefe = jefe if jefe is not None and jefe.pk != usuario.pk else None
            if usuario.supervisor_id != getattr(nuevo_jefe, "pk", None):
                usuario.supervisor = nuevo_jefe
                usuario.save(update_fields=["supervisor"])

    return ocupantes_por_puesto


def _respuestas(evaluacion, campo_puntaje, campo_comentario, puntaje, comentario):
    datos = {}
    for item in evaluacion.respuestas.select_related("criterio"):
        fila = {campo_comentario: comentario}
        if item.criterio.es_escala:
            fila[campo_puntaje] = puntaje
        datos[item.pk] = fila
    return datos


def _avanzar_auto(evaluacion, usuario, enviar, puntaje=4):
    evaluacion.refresh_from_db()
    if evaluacion.estado != Evaluacion.Estado.AUTOEVALUACION:
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
    if evaluacion.estado != Evaluacion.Estado.SUPERVISOR:
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


CAT_GENERALES = "Competencias generales"
CAT_TECNICO = "Desempeño técnico"
CAT_FINAL = "Evaluación final"
CAT_OBS = "Observaciones y plan de mejora"

# Catálogo compartido: el nombre es la clave de upsert. Las plantillas eligen un subconjunto.
COMPETENCIAS_CATALOGO = {
    "Responsabilidad": (
        Competencia.Tipo.ACTITUDINAL,
        "Cumple sus funciones con autonomía, compromiso y en tiempo y forma.",
    ),
    "Liderazgo": (
        Competencia.Tipo.ACTITUDINAL,
        "Dirige equipos de trabajo con eficiencia, manteniendo el orden y la motivación.",
    ),
    "Comunicación": (
        Competencia.Tipo.ACTITUDINAL,
        "Se comunica con claridad con jefaturas, pares, clientes internos y operarios.",
    ),
    "Compromiso": (
        Competencia.Tipo.ACTITUDINAL,
        "Se involucra activamente en la gestión del área y en la mejora de procesos.",
    ),
    "Proactividad": (
        Competencia.Tipo.ACTITUDINAL,
        "Anticipa vencimientos y requerimientos, detecta desvíos y propone acciones.",
    ),
    "Organización": (
        Competencia.Tipo.ACTITUDINAL,
        "Mantiene información ordenada, actualizada y disponible para la operación.",
    ),
    "Organización y planificación": (
        Competencia.Tipo.ACTITUDINAL,
        "Gestiona plazos, vencimientos, prioridades y documentación de manera eficiente.",
    ),
    "Planificación": (
        Competencia.Tipo.ACTITUDINAL,
        "Organiza las tareas y prioridades de trabajo de manera eficiente.",
    ),
    "Seguridad e higiene": (
        Competencia.Tipo.ACTITUDINAL,
        "Promueve y controla el cumplimiento de normas de seguridad en todas las áreas.",
    ),
    "Coordinación general del taller": (
        Competencia.Tipo.TECNICA,
        "Supervisa los sectores mecánicos, de herrería y playa garantizando continuidad operativa.",
    ),
    "Control de calidad": (
        Competencia.Tipo.TECNICA,
        "Verifica los trabajos finalizados y asegura el cumplimiento técnico.",
    ),
    "Asignación de recursos": (
        Competencia.Tipo.TECNICA,
        "Distribuye personal, herramientas y materiales de forma eficiente.",
    ),
    "Comunicación con gerencia": (
        Competencia.Tipo.TECNICA,
        "Reporta incidencias, avances y resultados con claridad.",
    ),
    "Supervisión de seguridad": (
        Competencia.Tipo.TECNICA,
        "Asegura que el personal cumpla las normas y procedimientos internos.",
    ),
    "Ejecución de tareas técnicas": (
        Competencia.Tipo.TECNICA,
        "Realiza las intervenciones mecánicas, de herrería o mantenimiento según el procedimiento.",
    ),
    "Uso y cuidado de herramientas": (
        Competencia.Tipo.TECNICA,
        "Utiliza y conserva herramientas, recambios y equipos de forma responsable.",
    ),
    "Cumplimiento de procedimientos": (
        Competencia.Tipo.TECNICA,
        "Respeta los circuitos internos, órdenes de trabajo y estándares del taller.",
    ),
    "Calidad del trabajo realizado": (
        Competencia.Tipo.TECNICA,
        "Entrega trabajos conformes, sin retrabajo evitable y con el nivel técnico esperado.",
    ),
    "Orden y limpieza del puesto": (
        Competencia.Tipo.TECNICA,
        "Mantiene el puesto, la playa y las áreas de trabajo ordenados y seguros.",
    ),
    "Gestión de seguros": (
        Competencia.Tipo.TECNICA,
        "Administra correctamente altas, bajas, renovaciones y seguimiento de pólizas y siniestros.",
    ),
    "Denuncia y seguimiento de siniestros": (
        Competencia.Tipo.TECNICA,
        "Realiza denuncias en tiempo y forma y controla los reintegros correspondientes.",
    ),
    "Control administrativo": (
        Competencia.Tipo.TECNICA,
        "Controla estados de cuenta, pagos a proveedores, impuestos automotor e inmobiliario.",
    ),
    "Conciliación y registración": (
        Competencia.Tipo.TECNICA,
        "Registra y concilia seguros y movimientos administrativos en los sistemas utilizados.",
    ),
    "Uso de sistemas de gestión": (
        Competencia.Tipo.TECNICA,
        "Utiliza correctamente Bejerman, Excel y plataformas de aseguradoras para la gestión diaria.",
    ),
    "Cumplimiento de procesos": (
        Competencia.Tipo.TECNICA,
        "Respeta los procedimientos internos y los circuitos administrativos definidos.",
    ),
    "Carga de viajes/remitos": (
        Competencia.Tipo.TECNICA,
        "Registra datos de viajes y remitos con precisión.",
    ),
    "Verificación de datos": (
        Competencia.Tipo.TECNICA,
        "Controla la exactitud de la información antes de facturar o emitir documentación.",
    ),
    "Gestión de portales": (
        Competencia.Tipo.TECNICA,
        "Opera plataformas de clientes y portales de facturación de forma correcta.",
    ),
    "Reportes": (
        Competencia.Tipo.TECNICA,
        "Presenta planillas claras, oportunas y consistentes con la operación.",
    ),
    "Detección de inconsistencias": (
        Competencia.Tipo.TECNICA,
        "Identifica errores, diferencias de tarifas y desvíos, y los escala a tiempo.",
    ),
    "Coordinación de viajes y flota": (
        Competencia.Tipo.TECNICA,
        "Organiza viajes, unidades y choferes para cumplir la demanda operativa.",
    ),
    "Control documental de flota": (
        Competencia.Tipo.TECNICA,
        "Controla documentación de choferes, unidades, remitos y habilitaciones.",
    ),
    "Seguimiento de entregas": (
        Competencia.Tipo.TECNICA,
        "Monitorea desvíos, novedades de ruta y cumplimiento de entregas.",
    ),
    "Comunicación con operación y clientes": (
        Competencia.Tipo.TECNICA,
        "Coordina con clientes, choferes y áreas internas para resolver incidencias.",
    ),
    "Normas de tránsito y seguridad vial": (
        Competencia.Tipo.TECNICA,
        "Hace cumplir normas de tránsito, descansos y seguridad vial en la operación.",
    ),
    "Conducción segura": (
        Competencia.Tipo.TECNICA,
        "Conduce de forma segura, respetando normas de tránsito y políticas internas.",
    ),
    "Cuidado de la unidad": (
        Competencia.Tipo.TECNICA,
        "Mantiene la unidad en condiciones, reporta fallas y cuida el activo asignado.",
    ),
    "Cumplimiento de recorridos y horarios": (
        Competencia.Tipo.TECNICA,
        "Respeta recorridos, ventanas horarias y consignas de cada viaje.",
    ),
    "Documentación de viaje": (
        Competencia.Tipo.TECNICA,
        "Completa remitos, formularios y novedades del viaje de forma correcta.",
    ),
    "Atención al cliente en ruta": (
        Competencia.Tipo.TECNICA,
        "Brinda un trato correcto en carga, descarga y contacto con el cliente.",
    ),
    "Planificación y avance de obra": (
        Competencia.Tipo.TECNICA,
        "Planifica tareas, controla el avance y anticipa desvíos del cronograma.",
    ),
    "Control de calidad de ejecución": (
        Competencia.Tipo.TECNICA,
        "Verifica que la ejecución cumpla especificaciones técnicas y de calidad.",
    ),
    "Gestión de recursos y contratistas": (
        Competencia.Tipo.TECNICA,
        "Coordina personal, materiales y contratistas para sostener la obra.",
    ),
    "Seguridad en obra": (
        Competencia.Tipo.TECNICA,
        "Controla el cumplimiento de seguridad e higiene en el frente de trabajo.",
    ),
    "Reportes de obra": (
        Competencia.Tipo.TECNICA,
        "Informa avances, incidencias y necesidades a la gerencia con claridad.",
    ),
    "Coordinación del servicio al cliente": (
        Competencia.Tipo.TECNICA,
        "Organiza frecuencias, turnos y novedades del servicio contratado.",
    ),
    "Cumplimiento de frecuencias": (
        Competencia.Tipo.TECNICA,
        "Asegura el cumplimiento de horarios, recorridos y niveles de servicio.",
    ),
    "Gestión de novedades operativas": (
        Competencia.Tipo.TECNICA,
        "Registra y resuelve ausencias, desvíos y reclamos del servicio.",
    ),
    "Calidad del servicio": (
        Competencia.Tipo.TECNICA,
        "Controla la calidad percibida y la conformidad del contratante.",
    ),
    "Relación con el contratante": (
        Competencia.Tipo.TECNICA,
        "Mantiene un vínculo profesional, oportuno y resolutivo con el cliente.",
    ),
    "Administración de personal y legajos": (
        Competencia.Tipo.TECNICA,
        "Gestiona altas, bajas, legajos y documentación laboral de forma completa.",
    ),
    "Seguimiento de evaluaciones de desempeño": (
        Competencia.Tipo.TECNICA,
        "Acompaña ciclos, plantillas y devoluciones del proceso de evaluación.",
    ),
    "Obligaciones laborales": (
        Competencia.Tipo.TECNICA,
        "Controla vencimientos, liquidaciones y cumplimiento normativo laboral.",
    ),
    "Confidencialidad y trato": (
        Competencia.Tipo.TECNICA,
        "Resguarda información sensible y sostiene un trato respetuoso con las personas.",
    ),
    "Sistemas de gestión de RRHH": (
        Competencia.Tipo.TECNICA,
        "Utiliza correctamente los sistemas y planillas de administración de personal.",
    ),
    "Gestión de clientes y cuentas": (
        Competencia.Tipo.TECNICA,
        "Administra la cartera, el seguimiento comercial y la relación con cuentas clave.",
    ),
    "Seguimiento de oportunidades": (
        Competencia.Tipo.TECNICA,
        "Detecta y avanza oportunidades comerciales hasta el cierre o la baja fundada.",
    ),
    "Coordinación comercial-operativa": (
        Competencia.Tipo.TECNICA,
        "Alinea promesas comerciales con la capacidad operativa y administrativa.",
    ),
    "Negociación y cierre": (
        Competencia.Tipo.TECNICA,
        "Negocia condiciones y cierra acuerdos alineados a la política comercial.",
    ),
    "Reportes comerciales": (
        Competencia.Tipo.TECNICA,
        "Presenta tableros, forecast y novedades de la cartera con claridad.",
    ),
    "Desarrollo y mantenimiento de aplicaciones": (
        Competencia.Tipo.TECNICA,
        "Desarrolla, mantiene y mejora las aplicaciones internas de la empresa.",
    ),
    "Calidad y pruebas del software": (
        Competencia.Tipo.TECNICA,
        "Prueba cambios, controla regresiones y entrega software estable.",
    ),
    "Soporte a usuarios internos": (
        Competencia.Tipo.TECNICA,
        "Atiende incidentes y requerimientos de usuarios con criterio y seguimiento.",
    ),
    "Seguridad de la información": (
        Competencia.Tipo.TECNICA,
        "Aplica buenas prácticas de acceso, resguardo y confidencialidad de datos.",
    ),
    "Documentación técnica": (
        Competencia.Tipo.TECNICA,
        "Documenta soluciones, procesos y cambios para que el equipo pueda sostenerlos.",
    ),
    "Definición de estrategia y objetivos": (
        Competencia.Tipo.TECNICA,
        "Define rumbo, prioridades y objetivos de la organización.",
    ),
    "Toma de decisiones": (
        Competencia.Tipo.TECNICA,
        "Decide con información suficiente y asume las consecuencias operativas.",
    ),
    "Supervisión de gerencias": (
        Competencia.Tipo.TECNICA,
        "Conduce el tablero de gerencias y exige resultados con seguimiento.",
    ),
    "Gestión de resultados": (
        Competencia.Tipo.TECNICA,
        "Controla indicadores económicos, operativos y de calidad de servicio.",
    ),
    "Representación institucional": (
        Competencia.Tipo.TECNICA,
        "Representa a la empresa ante clientes, organismos y partes interesadas.",
    ),
    "Asesoramiento legal y normativo": (
        Competencia.Tipo.TECNICA,
        "Brinda criterio legal y normativo aplicable a la operación de la empresa.",
    ),
    "Seguridad e higiene laboral": (
        Competencia.Tipo.TECNICA,
        "Asesora y controla el cumplimiento de seguridad e higiene laboral.",
    ),
    "Medicina laboral y seguimiento": (
        Competencia.Tipo.TECNICA,
        "Acompaña exámenes preocupacionales, ausentismo y seguimiento médico laboral.",
    ),
    "Informes y recomendaciones": (
        Competencia.Tipo.TECNICA,
        "Entrega informes claros, accionables y en los plazos acordados.",
    ),
    "Cumplimiento normativo": (
        Competencia.Tipo.TECNICA,
        "Anticipa riesgos de incumplimiento y propone medidas de mitigación.",
    ),
    "Nivel de desempeño": (
        Competencia.Tipo.OBJETIVO,
        "(5) Sobresaliente, (4) Muy bueno, (3) Bueno, (2) Regular, (1) Insuficiente.",
    ),
    "Potencial de desarrollo": (
        Competencia.Tipo.OBJETIVO,
        "(5 a 4) Alto, (3) Medio, (2 a 1) Bajo.",
    ),
    "Fortalezas destacadas": (
        Competencia.Tipo.OBJETIVO,
        "Aspectos a destacar del desempeño en el período.",
    ),
    "Oportunidades de mejora": (
        Competencia.Tipo.OBJETIVO,
        "Desvíos, hábitos o conocimientos a reforzar en el próximo período.",
    ),
    "Capacitación sugerida": (
        Competencia.Tipo.OBJETIVO,
        "Formación, práctica o acompañamiento recomendado.",
    ),
    "Objetivos para el próximo período": (
        Competencia.Tipo.OBJETIVO,
        "Metas concretas a revisar en la siguiente evaluación.",
    ),
    "Aspectos a destacar / Observaciones generales": (
        Competencia.Tipo.OBJETIVO,
        "Comentarios abiertos de la devolución (fortalezas, contexto o acuerdos).",
    ),
}

CIERRE_ESCALA = ("Nivel de desempeño", "Potencial de desarrollo")
CIERRE_TEXTO = (
    "Fortalezas destacadas",
    "Oportunidades de mejora",
    "Capacitación sugerida",
    "Objetivos para el próximo período",
    "Aspectos a destacar / Observaciones generales",
)

# Basadas en las fichas PO060102 (Taller), PO060101 (Administración) y PO060109 (Logística).
PLANTILLAS_DESEMPENO = (
    {
        "nombre": "Evaluación de Desempeño · Taller (jefatura)",
        "descripcion": "Ficha tipo PO060102 para jefatura y supervisión de taller y playa.",
        "puestos": (
            "Gerencia de Taller y Mantenimiento de Flota",
            "Jefe de Taller",
            "Supervisor de Taller",
            "Supervisor de Playa",
        ),
        "generales": (
            "Responsabilidad",
            "Liderazgo",
            "Comunicación",
            "Compromiso",
            "Seguridad e higiene",
            "Planificación",
        ),
        "tecnicos": (
            "Coordinación general del taller",
            "Control de calidad",
            "Asignación de recursos",
            "Comunicación con gerencia",
            "Supervisión de seguridad",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Taller (operarios)",
        "descripcion": "Adaptación de la ficha de taller para oficios, depósito, playa y seguridad.",
        "puestos": (
            "Mecánicos",
            "Soldadura y Pintura",
            "Depósito de Herramientas",
            "Mantenimiento Edilicio",
            "Seguridad",
        ),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Seguridad e higiene",
            "Organización",
        ),
        "tecnicos": (
            "Ejecución de tareas técnicas",
            "Uso y cuidado de herramientas",
            "Cumplimiento de procedimientos",
            "Calidad del trabajo realizado",
            "Orden y limpieza del puesto",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Administración y Finanzas",
        "descripcion": "Ficha tipo PO060101 para administración general, compras, pagos y coordinación contable.",
        "puestos": (
            "Gerencia de Administración y Finanzas",
            "Compras",
            "Pagos",
            "Contable",
        ),
        "generales": (
            "Responsabilidad",
            "Organización y planificación",
            "Comunicación",
            "Proactividad",
            "Compromiso",
        ),
        "tecnicos": (
            "Gestión de seguros",
            "Denuncia y seguimiento de siniestros",
            "Control administrativo",
            "Conciliación y registración",
            "Uso de sistemas de gestión",
            "Cumplimiento de procesos",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Logística",
        "descripcion": "Ficha tipo PO060109 para facturación, remitos y gestión documental.",
        "puestos": (
            "Facturación y Cobranzas",
            "Gestión Documental",
        ),
        "generales": (
            "Responsabilidad",
            "Organización",
            "Comunicación",
            "Compromiso",
            "Proactividad",
        ),
        "tecnicos": (
            "Carga de viajes/remitos",
            "Verificación de datos",
            "Gestión de portales",
            "Reportes",
            "Detección de inconsistencias",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Transporte y logística (coordinación)",
        "descripcion": "Coordinación de flota, viajes y operación de transporte.",
        "puestos": (
            "Gerencia de Transporte y Logística",
            "Coordinador Logístico",
            "Operación de Transporte",
            "Gestión y Control de Flota",
        ),
        "generales": (
            "Responsabilidad",
            "Liderazgo",
            "Comunicación",
            "Compromiso",
            "Planificación",
            "Proactividad",
        ),
        "tecnicos": (
            "Coordinación de viajes y flota",
            "Control documental de flota",
            "Seguimiento de entregas",
            "Comunicación con operación y clientes",
            "Normas de tránsito y seguridad vial",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Choferes",
        "descripcion": "Desempeño de conducción, cuidado de unidad y servicio en ruta.",
        "puestos": (
            "Choferes",
            "Choferes / Conductores",
        ),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Seguridad e higiene",
            "Proactividad",
        ),
        "tecnicos": (
            "Conducción segura",
            "Cuidado de la unidad",
            "Cumplimiento de recorridos y horarios",
            "Documentación de viaje",
            "Atención al cliente en ruta",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Obras y sustentabilidad",
        "descripcion": "Planificación, ejecución y control de obras.",
        "puestos": (
            "Gerencia de Obras y Sustentabilidad",
            "Director de Obra",
            "Planificación de Proyectos",
            "Operación y Ejecución de Obras",
        ),
        "generales": (
            "Responsabilidad",
            "Liderazgo",
            "Comunicación",
            "Compromiso",
            "Planificación",
            "Seguridad e higiene",
        ),
        "tecnicos": (
            "Planificación y avance de obra",
            "Control de calidad de ejecución",
            "Gestión de recursos y contratistas",
            "Seguridad en obra",
            "Reportes de obra",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Servicios empresariales",
        "descripcion": "Operación y calidad del servicio a clientes corporativos.",
        "puestos": (
            "Gerencia de Servicios Empresariales",
            "Operaciones de Servicios Empresariales",
        ),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Organización",
            "Proactividad",
        ),
        "tecnicos": (
            "Coordinación del servicio al cliente",
            "Cumplimiento de frecuencias",
            "Gestión de novedades operativas",
            "Calidad del servicio",
            "Relación con el contratante",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Recursos Humanos",
        "descripcion": "Gestión de personal, confidencialidad y proceso de desempeño.",
        "puestos": (
            "Gerente de RRHH",
            "Analistas RRHH",
        ),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Organización y planificación",
            "Proactividad",
        ),
        "tecnicos": (
            "Administración de personal y legajos",
            "Seguimiento de evaluaciones de desempeño",
            "Obligaciones laborales",
            "Confidencialidad y trato",
            "Sistemas de gestión de RRHH",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Comercial",
        "descripcion": "Cartera, negociación y coordinación con la operación.",
        "puestos": ("Gerencia Comercial",),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Proactividad",
            "Organización",
        ),
        "tecnicos": (
            "Gestión de clientes y cuentas",
            "Seguimiento de oportunidades",
            "Coordinación comercial-operativa",
            "Negociación y cierre",
            "Reportes comerciales",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Sistemas",
        "descripcion": "Desarrollo, soporte y seguridad de las aplicaciones internas.",
        "puestos": (
            "Gerencia de Sistemas",
            "Desarrollo de Software y Aplicaciones",
        ),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Organización",
            "Proactividad",
        ),
        "tecnicos": (
            "Desarrollo y mantenimiento de aplicaciones",
            "Calidad y pruebas del software",
            "Soporte a usuarios internos",
            "Seguridad de la información",
            "Documentación técnica",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Dirección",
        "descripcion": "Conducción estratégica y supervisión de gerencias.",
        "puestos": (
            "Presidente y CEO",
            "Vicepresidente",
            "Gerente General",
        ),
        "generales": (
            "Responsabilidad",
            "Liderazgo",
            "Comunicación",
            "Compromiso",
            "Planificación",
        ),
        "tecnicos": (
            "Definición de estrategia y objetivos",
            "Toma de decisiones",
            "Supervisión de gerencias",
            "Gestión de resultados",
            "Representación institucional",
        ),
    },
    {
        "nombre": "Evaluación de Desempeño · Consultoría externa",
        "descripcion": "Asesoramiento en legales, seguridad e higiene y medicina laboral.",
        "puestos": ("Consultoría Externa",),
        "generales": (
            "Responsabilidad",
            "Comunicación",
            "Compromiso",
            "Proactividad",
        ),
        "tecnicos": (
            "Asesoramiento legal y normativo",
            "Seguridad e higiene laboral",
            "Medicina laboral y seguimiento",
            "Informes y recomendaciones",
            "Cumplimiento normativo",
        ),
    },
)

PLANTILLA_DEFAULT_NOMBRE = "Evaluación de Desempeño · Recursos Humanos"
PLANTILLA_LEGACY_NOMBRE = "Plantilla mixta anual"


def _peso_igual(cantidad):
    if cantidad <= 0:
        return Decimal("0")
    return (Decimal("100") / Decimal(cantidad)).quantize(Decimal("0.01"))


def _upsert_competencia(empresa, nombre, tipo, descripcion):
    competencia, _ = _upsert_named(
        Competencia,
        empresa,
        nombre,
        descripcion=descripcion,
        tipo=tipo,
        activa=True,
    )
    return competencia


def _upsert_criterio(plantilla, competencia, campos):
    criterio, created = PlantillaCriterio.objects.get_or_create(
        plantilla=plantilla,
        competencia=competencia,
        defaults=campos,
    )
    if not created:
        for clave, valor in campos.items():
            setattr(criterio, clave, valor)
        criterio.save()
    return criterio


def _cargar_criterios_plantilla(plantilla, competencias, spec):
    generales = spec["generales"]
    tecnicos = spec["tecnicos"]
    n_escala = len(generales) + len(tecnicos) + len(CIERRE_ESCALA)
    peso = _peso_igual(n_escala)
    orden = 1
    usados = []

    def _agregar(nombres, categoria, tipo_item, ponderacion):
        nonlocal orden
        for nombre in nombres:
            competencia = competencias[nombre]
            campos = {
                "orden": orden,
                "categoria": categoria,
                "tipo_item": tipo_item,
                "escala_min": 1,
                "escala_max": 5,
                "ponderacion": ponderacion,
                "comentario_empleado_obligatorio": False,
                "comentario_supervisor_obligatorio": False,
            }
            usados.append(_upsert_criterio(plantilla, competencia, campos).pk)
            orden += 1

    _agregar(generales, CAT_GENERALES, PlantillaCriterio.TipoItem.ESCALA, peso)
    _agregar(tecnicos, CAT_TECNICO, PlantillaCriterio.TipoItem.ESCALA, peso)
    _agregar(CIERRE_ESCALA, CAT_FINAL, PlantillaCriterio.TipoItem.ESCALA, peso)
    _agregar(CIERRE_TEXTO, CAT_OBS, PlantillaCriterio.TipoItem.TEXTO, Decimal("0"))

    sobrantes = PlantillaCriterio.objects.filter(plantilla=plantilla).exclude(
        pk__in=usados
    )
    for criterio in sobrantes:
        if not criterio.respuestas.exists():
            criterio.delete()


def _asignar_puestos_exclusivos(plantilla, nombres_puestos, puestos_por_nombre):
    for nombre in nombres_puestos:
        puesto = puestos_por_nombre.get(nombre)
        if puesto is None:
            continue
        PlantillaPuesto.objects.filter(puesto=puesto).exclude(
            plantilla=plantilla
        ).delete()
        PlantillaPuesto.objects.get_or_create(plantilla=plantilla, puesto=puesto)


def _desactivar_plantilla_legacy(empresa):
    legacy = PlantillaEvaluacion.objects.filter(
        empresa=empresa, nombre=PLANTILLA_LEGACY_NOMBRE
    ).first()
    if legacy is None:
        return
    legacy.activa = False
    legacy.save(update_fields=["activa"])
    PlantillaPuesto.objects.filter(plantilla=legacy).delete()


def _seed_competencias_y_plantillas(empresa):
    """Crea el catálogo de competencias y una plantilla por familia de puestos."""
    competencias = {
        nombre: _upsert_competencia(empresa, nombre, tipo, descripcion)
        for nombre, (tipo, descripcion) in COMPETENCIAS_CATALOGO.items()
    }
    puestos_por_nombre = {
        puesto.nombre: puesto
        for puesto in Puesto.objects.filter(empresa=empresa, activo=True)
    }
    plantillas = {}
    puestos_asignados = set()
    for spec in PLANTILLAS_DESEMPENO:
        plantilla, _ = _upsert_named(
            PlantillaEvaluacion,
            empresa,
            spec["nombre"],
            tipo=PlantillaEvaluacion.Tipo.MIXTA,
            descripcion=spec["descripcion"],
            activa=True,
        )
        _cargar_criterios_plantilla(plantilla, competencias, spec)
        _asignar_puestos_exclusivos(plantilla, spec["puestos"], puestos_por_nombre)
        plantillas[spec["nombre"]] = plantilla
        puestos_asignados.update(spec["puestos"])

    default = plantillas[PLANTILLA_DEFAULT_NOMBRE]
    for nombre, puesto in puestos_por_nombre.items():
        if nombre in puestos_asignados:
            continue
        PlantillaPuesto.objects.filter(puesto=puesto).exclude(plantilla=default).delete()
        PlantillaPuesto.objects.get_or_create(plantilla=default, puesto=puesto)

    _desactivar_plantilla_legacy(empresa)
    return competencias, plantillas, default


def _completar_item_demo(item, evaluacion):
    if evaluacion.estado != Evaluacion.Estado.AUTOEVALUACION:
        if item.criterio.es_escala and item.puntaje_empleado is None:
            item.puntaje_empleado = 4
        if not (item.comentario_empleado or "").strip():
            item.comentario_empleado = "Comentario demo de autoevaluación."
    if evaluacion.estado not in (
        Evaluacion.Estado.AUTOEVALUACION,
        Evaluacion.Estado.SUPERVISOR,
    ):
        if item.criterio.es_escala and item.puntaje_supervisor is None:
            item.puntaje_supervisor = 5
        if not (item.comentario_supervisor or "").strip():
            item.comentario_supervisor = "Comentario demo del supervisor."
    item.save()


def _sincronizar_respuestas(evaluacion):
    criterios = list(evaluacion.plantilla.criterios.all())
    existentes = {
        item.criterio_id: item
        for item in evaluacion.respuestas.select_related("criterio")
    }
    for criterio in criterios:
        item = existentes.get(criterio.pk)
        if item is None:
            item = RespuestaItem.objects.create(evaluacion=evaluacion, criterio=criterio)
        _completar_item_demo(item, evaluacion)


def _alinear_evaluaciones_ciclo(ciclo):
    """Reasigna plantilla solo si la evaluación todavía no avanzó el flujo."""
    editables = (Evaluacion.Estado.AUTOEVALUACION,)
    for evaluacion in Evaluacion.objects.filter(ciclo=ciclo).select_related(
        "evaluado", "evaluado__puesto", "plantilla"
    ):
        esperada = resolver_plantilla(evaluacion.evaluado, ciclo)
        if evaluacion.plantilla_id != esperada.pk and evaluacion.estado in editables:
            evaluacion.respuestas.all().delete()
            evaluacion.plantilla = esperada
            evaluacion.save(update_fields=["plantilla"])
        _sincronizar_respuestas(evaluacion)


def _ocupante_puesto(empresa, nombre_puesto):
    puesto = Puesto.objects.filter(
        empresa=empresa, nombre=nombre_puesto, activo=True
    ).first()
    if puesto is None:
        return None
    return (
        Usuario.objects.filter(empresa=empresa, puesto=puesto, is_active=True)
        .order_by("pk")
        .first()
    )


def _cerrar_si_pendiente(evaluacion, usuario):
    evaluacion.refresh_from_db()
    if evaluacion.estado == Evaluacion.Estado.PENDIENTE_CONFORMIDAD:
        firmar_conformidad(evaluacion, usuario, "127.0.0.1")


def _avanzar_muestra_areas(ciclo, empresa, emails_reservados):
    """Deja evaluaciones de otras áreas en distintos estados, inspiradas en las fichas."""
    muestras = (
        ("Jefe de Taller", "auto", 5),
        ("Contable", "cerrada", 5),
        ("Facturación y Cobranzas", "auto", 4),
        ("Choferes", "borrador", 4),
        ("Mecánicos", "cerrada", 4),
        ("Desarrollo de Software y Aplicaciones", "auto", 4),
    )
    for nombre_puesto, etapa, puntaje in muestras:
        usuario = _ocupante_puesto(empresa, nombre_puesto)
        if usuario is None or usuario.email.lower() in emails_reservados:
            continue
        evaluacion = Evaluacion.objects.filter(ciclo=ciclo, evaluado=usuario).first()
        if evaluacion is None:
            continue
        _avanzar_auto(evaluacion, usuario, enviar=(etapa != "borrador"), puntaje=puntaje)
        if etapa == "cerrada" and evaluacion.evaluador_id:
            evaluacion.refresh_from_db()
            _avanzar_supervisor(
                evaluacion, evaluacion.evaluador, cerrar=True, puntaje=puntaje
            )
            _cerrar_si_pendiente(evaluacion, usuario)


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

    org = _seed_organigrama(empresa_a)
    area = org["area_rrhh"]
    puesto_jefe = org["puesto_supervisor"]
    puesto_analista = org["puesto_empleado"]
    _competencias, _plantillas, plantilla = _seed_competencias_y_plantillas(empresa_a)

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
    _seed_usuarios_puestos(empresa_a, DEMO_PASSWORD)
    supervisor.refresh_from_db()
    empleado_1.refresh_from_db()
    empleado_2.refresh_from_db()
    empleado_3.refresh_from_db()
    admin_b, _ = _upsert_usuario(
        EMAIL_RRHH_B,
        empresa_b,
        DEMO_PASSWORD,
        rol=Usuario.Rol.ADMIN_RRHH,
        first_name="Bárbara",
        last_name="Beta",
    )

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

    _alinear_evaluaciones_ciclo(ciclo)

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
        _cerrar_si_pendiente(ev3, empleado_3)
    if ev_sup is not None:
        _avanzar_auto(ev_sup, supervisor, enviar=False, puntaje=3)

    _avanzar_muestra_areas(ciclo, empresa_a, _EMAILS_RESERVADOS)

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
