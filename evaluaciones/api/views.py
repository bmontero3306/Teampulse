from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.permissions import EmpresaActivaPermission, RolPermission
from auditoria.services import registrar_auditoria
from cuentas.models import Usuario
from evaluaciones.api.serializers import (
    AutoevaluacionInputSerializer,
    CicloSerializer,
    EvaluacionDetalleSerializer,
    EvaluacionListaSerializer,
    FirmarInputSerializer,
    PlantillaSerializer,
    ReasignarInputSerializer,
    ReunionInputSerializer,
    ReprogramarSerializer,
    SupervisarInputSerializer,
)
from evaluaciones.exceptions import EvaluacionesError
from evaluaciones.models import CicloEvaluacion, Evaluacion, PlantillaEvaluacion
from evaluaciones.pdf import CONTENT_TYPE_PDF, exportar_resultado_pdf, nombre_archivo_pdf
from evaluaciones.services import (
    _es_rrhh,
    activar_ciclo,
    cancelar_ciclo,
    candidatos_evaluador,
    duplicar_plantilla,
    firmar_conformidad,
    guardar_autoevaluacion,
    guardar_eval_supervisor,
    omitir_reunion_feedback,
    pausar_ciclo,
    reasignar_evaluador,
    registrar_reunion_feedback,
    reprogramar_ciclo,
)
from evaluaciones.views import ROLES_CRUD as ROLES_PLANTILLA_CRUD
from evaluaciones.views import ROLES_LECTURA as ROLES_PLANTILLA_LECTURA
from evaluaciones.views_ciclos import ROLES_CRUD as ROLES_CICLO_CRUD
from evaluaciones.views_ciclos import ROLES_LECTURA as ROLES_CICLO_LECTURA
from evaluaciones.views_flujo import ROLES_FLUJO_PROPIO, _ip, _puede_ver_resultado


def _map_respuestas(filas, puntaje, comentario):
    datos = {}
    for fila in filas:
        datos[fila["id"]] = {
            puntaje: fila.get(puntaje),
            comentario: fila.get(comentario) or "",
        }
    return datos


def _error(exc: EvaluacionesError):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PlantillaViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaSerializer
    permission_classes = [RolPermission, EmpresaActivaPermission]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.roles_permitidos = ROLES_PLANTILLA_LECTURA
        else:
            self.roles_permitidos = ROLES_PLANTILLA_CRUD
        return super().get_permissions()

    def get_queryset(self):
        return (
            PlantillaEvaluacion.objects.for_empresa(self.request.empresa)
            .prefetch_related("criterios__competencia", "puestos")
            .order_by("nombre")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["empresa"] = getattr(self.request, "empresa", None)
        return ctx

    def perform_destroy(self, instance):
        instance.activa = False
        instance.save(update_fields=["activa"])

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        nueva = duplicar_plantilla(self.get_object())
        return Response(self.get_serializer(nueva).data, status=status.HTTP_201_CREATED)


class CicloViewSet(viewsets.ModelViewSet):
    serializer_class = CicloSerializer
    permission_classes = [RolPermission, EmpresaActivaPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.roles_permitidos = ROLES_CICLO_LECTURA
        else:
            self.roles_permitidos = ROLES_CICLO_CRUD
        return super().get_permissions()

    def get_queryset(self):
        return (
            CicloEvaluacion.objects.for_empresa(self.request.empresa)
            .select_related("plantilla_default")
            .prefetch_related("areas")
            .annotate(
                total_evals=Count("evaluaciones", distinct=True),
                sin_evaluador_count=Count(
                    "evaluaciones",
                    filter=Q(evaluaciones__sin_evaluador=True),
                    distinct=True,
                ),
            )
            .order_by("-fecha_inicio", "nombre")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["empresa"] = getattr(self.request, "empresa", None)
        return ctx

    def perform_create(self, serializer):
        ciclo = serializer.save()
        registrar_auditoria(self.request, accion="crear", instance=ciclo)

    def _transicion(self, fn):
        try:
            ciclo = fn(self.get_object(), self.request.user, request=self.request)
        except EvaluacionesError as exc:
            return _error(exc)
        if isinstance(ciclo, tuple):
            ciclo = ciclo[0]
        return Response(self.get_serializer(self.get_queryset().get(pk=ciclo.pk)).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        return self._transicion(activar_ciclo)

    @action(detail=True, methods=["post"])
    def pausar(self, request, pk=None):
        return self._transicion(pausar_ciclo)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        return self._transicion(cancelar_ciclo)

    @action(detail=True, methods=["post"])
    def reprogramar(self, request, pk=None):
        serializer = ReprogramarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ciclo = reprogramar_ciclo(
                self.get_object(),
                serializer.validated_data["fecha_inicio"],
                serializer.validated_data["fecha_cierre"],
                request.user,
                request=request,
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return Response(self.get_serializer(self.get_queryset().get(pk=ciclo.pk)).data)

    @action(detail=True, methods=["get"])
    def participantes(self, request, pk=None):
        ciclo = self.get_object()
        qs = (
            Evaluacion.objects.for_empresa(request.empresa)
            .filter(ciclo=ciclo)
            .select_related("evaluado", "evaluador", "puesto", "ciclo", "plantilla")
        )
        return Response(EvaluacionListaSerializer(qs, many=True).data)


class EvaluacionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = ROLES_FLUJO_PROPIO

    def get_queryset(self):
        return (
            Evaluacion.objects.for_empresa(self.request.empresa)
            .select_related(
                "ciclo",
                "evaluado",
                "evaluador",
                "puesto",
                "plantilla",
                "empresa",
            )
            .prefetch_related("respuestas__criterio__competencia")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EvaluacionDetalleSerializer
        return EvaluacionListaSerializer

    def _detalle(self, evaluacion):
        evaluacion = self.get_queryset().get(pk=evaluacion.pk)
        return Response(EvaluacionDetalleSerializer(evaluacion).data)

    @action(detail=False, methods=["get"])
    def mias(self, request):
        qs = self.get_queryset().filter(evaluado=request.user)
        return Response(EvaluacionListaSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def equipo(self, request):
        if request.user.rol != Usuario.Rol.SUPERVISOR:
            return Response(
                {"detail": "No tenés permiso para acceder a esta sección."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = self.get_queryset().filter(evaluador=request.user)
        return Response(EvaluacionListaSerializer(qs, many=True).data)

    @action(detail=True, methods=["get", "put"], url_path="autoevaluacion")
    def autoevaluacion(self, request, pk=None):
        evaluacion = self.get_object()
        if evaluacion.evaluado_id != request.user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            return self._detalle(evaluacion)
        serializer = AutoevaluacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            evaluacion = guardar_autoevaluacion(
                evaluacion,
                _map_respuestas(
                    serializer.validated_data["respuestas"],
                    "puntaje_empleado",
                    "comentario_empleado",
                ),
                serializer.validated_data["enviar"],
                request.user,
                request=request,
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)

    @action(detail=True, methods=["get", "put"])
    def supervisar(self, request, pk=None):
        evaluacion = self.get_object()
        if request.user.rol != Usuario.Rol.SUPERVISOR or evaluacion.evaluador_id != request.user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            return self._detalle(evaluacion)
        serializer = SupervisarInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            evaluacion = guardar_eval_supervisor(
                evaluacion,
                _map_respuestas(
                    serializer.validated_data["respuestas"],
                    "puntaje_supervisor",
                    "comentario_supervisor",
                ),
                serializer.validated_data.get("feedback_supervisor", ""),
                serializer.validated_data["cerrar"],
                request.user,
                request=request,
                habilitar_reunion=serializer.validated_data["habilitar_reunion"],
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)

    @action(detail=True, methods=["get"])
    def resultado(self, request, pk=None):
        evaluacion = self.get_object()
        if not _puede_ver_resultado(request.user, evaluacion):
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = EvaluacionDetalleSerializer(evaluacion).data
        if not evaluacion.comparacion_revelada and not _es_rrhh(request.user):
            for item in data["respuestas"]:
                item["puntaje_supervisor"] = None
                item["comentario_supervisor"] = ""
                item["brecha"] = None
            data["feedback_supervisor"] = ""
        data["puede_firmar"] = (
            evaluacion.evaluado_id == request.user.pk
            and evaluacion.estado == Evaluacion.Estado.PENDIENTE_CONFORMIDAD
        )
        data["puede_reunion"] = (
            evaluacion.estado == Evaluacion.Estado.PENDIENTE_COMPARACION
            and (
                evaluacion.evaluador_id == request.user.pk or _es_rrhh(request.user)
            )
        )
        return Response(data)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        evaluacion = self.get_object()
        serializer = FirmarInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            evaluacion = firmar_conformidad(
                evaluacion,
                request.user,
                _ip(request),
                observacion=serializer.validated_data.get("observacion"),
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)

    @action(detail=True, methods=["post"], url_path="reunion")
    def reunion(self, request, pk=None):
        evaluacion = self.get_object()
        serializer = ReunionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            evaluacion = registrar_reunion_feedback(
                evaluacion,
                serializer.validated_data["reunion_fecha"],
                serializer.validated_data["reunion_notas"],
                request.user,
                request=request,
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)

    @action(detail=True, methods=["post"], url_path="omitir-reunion")
    def omitir_reunion(self, request, pk=None):
        evaluacion = self.get_object()
        try:
            evaluacion = omitir_reunion_feedback(evaluacion, request.user, request=request)
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)

    @action(detail=True, methods=["get", "post"])
    def reasignar(self, request, pk=None):
        if not _es_rrhh(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        evaluacion = self.get_object()
        if request.method == "GET":
            candidatos = candidatos_evaluador(evaluacion)
            return Response(
                [
                    {
                        "id": u.pk,
                        "nombre": u.get_full_name() or u.email,
                        "email": u.email,
                        "rol": u.rol,
                    }
                    for u in candidatos
                ]
            )
        serializer = ReasignarInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluador = get_object_or_404(
            Usuario.objects.for_empresa(request.empresa),
            pk=serializer.validated_data["evaluador"],
        )
        try:
            evaluacion = reasignar_evaluador(
                evaluacion, evaluador, request.user, request=request
            )
        except EvaluacionesError as exc:
            return _error(exc)
        return self._detalle(evaluacion)


class ResultadoPdfView(APIView):
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = ROLES_FLUJO_PROPIO

    def get(self, request, pk):
        evaluacion = get_object_or_404(
            Evaluacion.objects.for_empresa(request.empresa).select_related(
                "ciclo", "empresa", "evaluado", "evaluador", "puesto", "plantilla"
            ),
            pk=pk,
        )
        if not _puede_ver_resultado(request.user, evaluacion):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not evaluacion.esta_cerrada and not _es_rrhh(request.user):
            if not evaluacion.comparacion_revelada:
                return Response(status=status.HTTP_403_FORBIDDEN)
        contenido = exportar_resultado_pdf(evaluacion, usuario=request.user)
        response = HttpResponse(contenido, content_type=CONTENT_TYPE_PDF)
        response["Content-Disposition"] = f'inline; filename="{nombre_archivo_pdf(evaluacion)}"'
        return response
