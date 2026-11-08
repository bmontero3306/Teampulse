from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.ayuda import grupos_paginas, pagina_por_slug, paginas_visibles
from app.services import (
    accesos_rapidos_empleado,
    ciclo_activo,
    kpis_ciclo,
    pendientes_empleado,
    resumen_equipo,
)
from cuentas.models import Usuario
from empresas.models import Empresa


def _pendiente_api(item):
    evaluacion = item["evaluacion"]
    pk = evaluacion.pk
    if item["tipo"] == "auto":
        href = f"/evaluaciones/{pk}/autoevaluacion"
    else:
        href = f"/evaluaciones/{pk}/resultado"
    return {
        "evaluacion_id": pk,
        "tipo": item["tipo"],
        "accion": item["accion"],
        "href": href,
        "estado": evaluacion.estado,
        "ciclo": evaluacion.ciclo.nombre,
    }


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresa = getattr(request, "empresa", None)
        rol = getattr(user, "rol", None)
        ciclo = ciclo_activo(empresa)
        es_superadmin = rol == Usuario.Rol.SUPERADMIN
        es_admin = rol == Usuario.Rol.ADMIN_RRHH or (es_superadmin and empresa is not None)
        es_supervisor = rol == Usuario.Rol.SUPERVISOR
        es_empleado = rol in {Usuario.Rol.EMPLEADO, Usuario.Rol.SUPERVISOR}
        pendientes = pendientes_empleado(user, empresa, ciclo) if es_empleado else []
        equipo = resumen_equipo(user, empresa, ciclo) if es_supervisor else None
        ciclo_data = None
        if ciclo is not None:
            ciclo_data = {
                "id": ciclo.pk,
                "nombre": ciclo.nombre,
                "estado": ciclo.estado,
                "fecha_inicio": ciclo.fecha_inicio,
                "fecha_cierre": ciclo.fecha_cierre,
            }
        equipo_data = None
        if equipo is not None:
            equipo_data = {
                "total": equipo["total"],
                "auto_hechas": equipo["auto_hechas"],
                "completitud": equipo["completitud"],
                "href": "/evaluaciones/equipo",
                "alertas_sin_auto": [
                    {
                        "id": ev.pk,
                        "evaluado": ev.evaluado.get_full_name() or ev.evaluado.email,
                        "estado": ev.estado,
                    }
                    for ev in equipo["alertas_sin_auto"]
                ],
                "evaluaciones": [
                    {
                        "id": ev.pk,
                        "evaluado": ev.evaluado.get_full_name() or ev.evaluado.email,
                        "estado": ev.estado,
                        "estado_display": ev.get_estado_display(),
                    }
                    for ev in equipo["evaluaciones"]
                ],
            }
        return Response(
            {
                "ciclo_activo": ciclo_data,
                "kpis": kpis_ciclo(empresa, ciclo) if es_admin else None,
                "pendientes": [_pendiente_api(item) for item in pendientes],
                "accesos_rapidos": (
                    [
                        {
                            "clave": acceso["clave"],
                            "etiqueta": acceso["etiqueta"],
                            "href": _href_acceso(acceso),
                        }
                        for acceso in accesos_rapidos_empleado(pendientes)
                    ]
                    if es_empleado
                    else []
                ),
                "equipo": equipo_data,
                "empresas_plataforma": (
                    list(Empresa.objects.order_by("nombre").values("id", "nombre", "estado"))
                    if es_superadmin
                    else []
                ),
                "mostrar_pendientes": es_empleado,
                "mostrar_equipo": es_supervisor,
                "mostrar_kpis": es_admin,
                "mostrar_empresas": es_superadmin,
            }
        )


def _href_acceso(acceso):
    clave = acceso["clave"]
    if clave == "mias":
        return "/evaluaciones/mias"
    return acceso["href"].rstrip("/") or acceso["href"]


class AyudaIndexView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request, "empresa", None)
        paginas = []
        for pagina in paginas_visibles(request.user, empresa):
            paginas.append(_pagina_publica(pagina))
        return Response(
            {
                "paginas": paginas,
                "grupos": [
                    {
                        "nombre": grupo["nombre"],
                        "paginas": [_pagina_publica(p) for p in grupo["paginas"]],
                    }
                    for grupo in grupos_paginas(request.user, empresa)
                ],
            }
        )


class AyudaPaginaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        pagina = pagina_por_slug(slug)
        visibles = {p["slug"] for p in paginas_visibles(request.user, getattr(request, "empresa", None))}
        if pagina is None or slug not in visibles:
            return Response({"detail": "No encontrada."}, status=404)
        data = _pagina_publica(pagina)
        data["cuerpo"] = CUERPO.get(slug, pagina["resumen"])
        return Response(data)


def _pagina_publica(pagina):
    return {
        "slug": pagina["slug"],
        "titulo": pagina["titulo"],
        "resumen": pagina["resumen"],
        "icono": pagina["icono"],
        "grupo": pagina["grupo"],
    }


CUERPO = {
    "inicio": [
        "TeamPulse gestiona el desempeño por empresa: autoevaluación, evaluación del supervisor, firma de conformidad y reportes.",
        "1. Armar la organización: áreas, puestos, organigrama y competencias.",
        "2. Definir qué se evalúa: una plantilla reúne criterios, escalas y ponderaciones.",
        "3. Abrir un ciclo: RRHH lo crea y, al activarlo, se generan las evaluaciones de quienes tienen puesto.",
        "4. Recorrer el flujo: empleado, supervisor, reunión opcional y firma.",
        "5. Cerrar y reportar: exportar reportes y consultar la auditoría.",
    ],
    "roles": [
        "Superadmin: administra empresas de la plataforma y entra al contexto de cada una.",
        "Admin RRHH: usuarios, organización, plantillas, ciclos, reportes y auditoría de su empresa.",
        "Supervisor: ve el organigrama, las plantillas y los ciclos, y evalúa a su equipo.",
        "Empleado: completa su autoevaluación y firma la conformidad.",
    ],
    "organizacion": [
        "Cada persona pertenece a un área y ocupa un puesto. El puesto superior define el organigrama.",
        "Las competencias se reutilizan en las plantillas. Desactivar no borra el historial.",
    ],
    "plantillas": [
        "Una plantilla agrupa criterios de escala o texto, con ponderación y comentarios obligatorios.",
        "Se puede asociar a puestos. Si un puesto tiene plantilla propia, gana sobre la del ciclo.",
        "Duplicar copia criterios y puestos sin compartir el mismo registro.",
    ],
    "ciclos": [
        "Estados: borrador, activo, pausado, cerrado y cancelado. Solo puede haber un ciclo activo por empresa.",
        "Al activar un borrador se crean las evaluaciones de los participantes con puesto.",
        "Pausar impide editar evaluaciones. Reprogramar cambia las fechas y avisa a los participantes.",
    ],
    "flujo": [
        "Pendiente de autoevaluación → borrador → enviada.",
        "El supervisor no ve la autoevaluación hasta que el empleado la envía.",
        "Al cerrar, el supervisor puede pedir reunión de feedback o pasar directo a la conformidad.",
        "Después de la reunión (o si se omite) el empleado firma o deja una observación.",
    ],
    "conformidad": [
        "La firma guarda fecha, IP y un hash de los puntajes.",
        "Conforme cierra la evaluación. Con observación queda cerrada con observación.",
        "El comprobante PDF está disponible cuando la comparación ya se reveló.",
    ],
    "notificaciones": [
        "Los avisos aparecen en la campana y en el listado. También se envían por email.",
        "El comando enviar_recordatorios avisa pendientes de un ciclo activo.",
    ],
    "reportes": [
        "El reporte filtra por ciclo, área, estado de conformidad y fechas.",
        "Se puede previsualizar y exportar a PDF o Excel. Cada exportación queda en la auditoría.",
    ],
    "auditoria": [
        "Se registran altas, ediciones, cambios de estado, login, firma y exportaciones.",
        "Las contraseñas y tokens no se guardan en el detalle.",
    ],
    "empresas": [
        "Una empresa activa permite el ingreso. Suspendida o inactiva, sus usuarios no entran.",
        "El superadmin elige la empresa de trabajo desde la barra superior. Esa elección no cambia la cuenta.",
    ],
}
