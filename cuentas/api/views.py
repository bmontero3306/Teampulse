from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.permissions import EmpresaActivaPermission, RolPermission
from app.navigation import items_navegacion
from auditoria.constants import Accion
from auditoria.services import registrar_auditoria
from cuentas.api.serializers import (
    CambioClaveSerializer,
    ResetConfirmarSerializer,
    ResetSolicitudSerializer,
    UsuarioSerializer,
    UsuarioWriteSerializer,
)
from cuentas.forms import ROLES_GESTION, RecuperarClaveForm
from cuentas.models import Usuario
from cuentas.services import asignar_clave_temporal
from empresas.models import Empresa
from notificaciones.models import Notificacion
from notificaciones.services import notificar
from organizacion.models import Area

RUTAS_SPA = {
    "dashboard": "/dashboard",
    "empresas": "/empresas",
    "usuarios": "/usuarios",
    "organigrama": "/organizacion",
    "plantillas": "/evaluaciones/plantillas",
    "ciclos": "/evaluaciones/ciclos",
    "equipo": "/evaluaciones/equipo",
    "mias": "/evaluaciones/mias",
    "reportes": "/reportes/iso",
    "auditoria": "/auditoria",
    "notificaciones": "/notificaciones",
    "ayuda": "/ayuda",
    "perfil": "/perfil",
}

MENSAJES_LOGIN = {
    "inactive": "Tu cuenta está desactivada.",
    "bloqueado": "Tu cuenta está bloqueada. Contactá a RRHH.",
    "empresa_suspendida": "La empresa está suspendida. No podés iniciar sesión.",
    "empresa_inactiva": "La empresa no está activa. No podés iniciar sesión.",
    "sin_empresa": "Tu cuenta no está asociada a una empresa.",
}


def motivo_rechazo_login(user):
    if not user.is_active:
        return MENSAJES_LOGIN["inactive"]
    if getattr(user, "bloqueado", False):
        return MENSAJES_LOGIN["bloqueado"]
    if getattr(user, "rol", None) == Usuario.Rol.SUPERADMIN:
        return None
    empresa = getattr(user, "empresa", None)
    if empresa is None:
        return MENSAJES_LOGIN["sin_empresa"]
    if empresa.estado == Empresa.Estado.SUSPENDIDA:
        return MENSAJES_LOGIN["empresa_suspendida"]
    if empresa.estado != Empresa.Estado.ACTIVA:
        return MENSAJES_LOGIN["empresa_inactiva"]
    return None


def emitir_token(user):
    from rest_framework.authtoken.models import Token

    Token.objects.filter(user=user).delete()
    return Token.objects.create(user=user)


def payload_usuario(user, request):
    empresa = getattr(request, "empresa", None)
    items = []
    for item in items_navegacion(user, empresa):
        items.append(
            {
                "clave": item["clave"],
                "etiqueta": item["etiqueta"],
                "icono": item["icono"],
                "href": RUTAS_SPA.get(item["clave"], item["href"]),
            }
        )
    no_leidas = 0
    if user.is_authenticated:
        qs = Notificacion.objects.filter(usuario=user, leida=False)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        no_leidas = qs.count()
    return {
        "usuario": UsuarioSerializer(user).data,
        "empresa_actual": (
            {"id": empresa.pk, "nombre": empresa.nombre, "estado": empresa.estado}
            if empresa is not None
            else None
        ),
        "nav": items,
        "notificaciones_no_leidas": no_leidas,
        "debe_cambiar_clave": bool(getattr(user, "must_change_password", False)),
    }


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(request, username=email, password=password)
        if user is None:
            user_login_failed.send(
                sender=Usuario,
                credentials={"email": email},
                request=request,
            )
            return Response(
                {"detail": "Email o contraseña incorrectos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        motivo = motivo_rechazo_login(user)
        if motivo:
            user_login_failed.send(
                sender=Usuario,
                credentials={"email": email},
                request=request,
            )
            return Response({"detail": motivo}, status=status.HTTP_400_BAD_REQUEST)
        token = emitir_token(user)
        user_logged_in.send(sender=user.__class__, request=request, user=user)
        data = payload_usuario(user, request)
        data["token"] = token.key
        return Response(data)


class LogoutView(APIView):
    permite_clave_pendiente = True

    def post(self, request):
        from rest_framework.authtoken.models import Token

        Token.objects.filter(user=request.user).delete()
        user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permite_clave_pendiente = True

    def get(self, request):
        return Response(payload_usuario(request.user, request))


class CambioClaveView(APIView):
    permite_clave_pendiente = True

    def post(self, request):
        serializer = CambioClaveSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": ["La contraseña actual no es correcta."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        token = emitir_token(user)
        data = payload_usuario(user, request)
        data["token"] = token.key
        return Response(data)


class ResetSolicitudView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ResetSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        form = RecuperarClaveForm(data={"email": email})
        form.is_valid()
        for usuario in form.get_users(email):
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            url = f"{settings.FRONTEND_ORIGIN}/recuperar/{uid}/{token}"
            send_mail(
                "Recuperar contraseña de TeamPulse",
                (
                    "Recibimos un pedido para restablecer tu contraseña.\n\n"
                    f"Abrí este enlace: {url}\n\n"
                    "Si no pediste el cambio, ignorá este mensaje."
                ),
                settings.DEFAULT_FROM_EMAIL,
                [usuario.email],
                fail_silently=True,
            )
        return Response(
            {
                "detail": "Si el correo está registrado, te enviamos un enlace para restablecer la clave."
            }
        )


class ResetConfirmarView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ResetConfirmarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            usuario = Usuario.objects.get(pk=uid)
        except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "El enlace no es válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(usuario, serializer.validated_data["token"]):
            return Response(
                {"detail": "El enlace no es válido o ya venció."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nueva = serializer.validated_data["new_password"]
        try:
            validate_password(nueva, usuario)
        except DjangoValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        usuario.set_password(nueva)
        usuario.must_change_password = False
        usuario.save(update_fields=["password", "must_change_password"])
        return Response({"detail": "Tu contraseña se actualizó. Ya podés iniciar sesión."})


class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [RolPermission, EmpresaActivaPermission]
    roles_permitidos = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = (
            Usuario.objects.for_empresa(self.request.empresa)
            .select_related("area", "puesto", "supervisor")
            .order_by("last_name", "first_name", "email")
        )
        rol = self.request.query_params.get("rol")
        if rol:
            qs = qs.filter(rol=rol)
        activo = self.request.query_params.get("activo")
        if activo == "1":
            qs = qs.filter(is_active=True)
        elif activo == "0":
            qs = qs.filter(is_active=False)
        area = self.request.query_params.get("area")
        if area:
            qs = qs.filter(area_id=area)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UsuarioWriteSerializer
        return UsuarioSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["empresa"] = getattr(self.request, "empresa", None)
        return ctx

    def perform_create(self, serializer):
        usuario = serializer.save()
        registrar_auditoria(self.request, Accion.CREAR, instance=usuario)
        notificar(
            tipo="usuario_creado",
            usuario=usuario,
            titulo="Tu cuenta fue creada",
            mensaje="Se creó tu usuario en TeamPulse. Debés cambiar la contraseña al ingresar.",
            url="/perfil",
            empresa=usuario.empresa,
        )

    def perform_update(self, serializer):
        usuario = serializer.save()
        notificar(
            tipo="usuario_modificado",
            usuario=usuario,
            titulo="Tus datos fueron actualizados",
            mensaje="Se modificaron los datos de tu cuenta en TeamPulse.",
            url="/perfil",
            empresa=usuario.empresa,
        )

    def _no_sobre_si_mismo(self, usuario):
        if usuario.pk == self.request.user.pk:
            return Response(
                {"detail": "No podés aplicar esta acción sobre tu propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        rechazo = self._no_sobre_si_mismo(usuario)
        if rechazo:
            return rechazo
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        notificar(
            tipo="usuario_desactivado",
            usuario=usuario,
            titulo="Tu cuenta fue desactivada",
            mensaje="Tu usuario en TeamPulse fue desactivado.",
            url="/login",
            empresa=usuario.empresa,
        )
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"])
    def bloquear(self, request, pk=None):
        usuario = self.get_object()
        rechazo = self._no_sobre_si_mismo(usuario)
        if rechazo:
            return rechazo
        usuario.bloqueado = True
        usuario.save(update_fields=["bloqueado"])
        notificar(
            tipo="usuario_bloqueado",
            usuario=usuario,
            titulo="Tu cuenta fue bloqueada",
            mensaje="Tu usuario en TeamPulse fue bloqueado. Contactá a RRHH.",
            url="/login",
            empresa=usuario.empresa,
        )
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"], url_path="reset-clave")
    def reset_clave(self, request, pk=None):
        usuario = self.get_object()
        rechazo = self._no_sobre_si_mismo(usuario)
        if rechazo:
            return rechazo
        clave = asignar_clave_temporal(usuario)
        usuario.save(update_fields=["password", "must_change_password"])
        notificar(
            tipo="usuario_reset_clave",
            usuario=usuario,
            titulo="Se restableció tu contraseña",
            mensaje="Tu contraseña fue restablecida. Vas a tener que cambiarla al ingresar.",
            url="/clave",
            empresa=usuario.empresa,
        )
        data = UsuarioSerializer(usuario).data
        data["clave_temporal"] = clave
        return Response(data)

    @action(detail=False, methods=["get"])
    def opciones(self, request):
        empresa = request.empresa
        return Response(
            {
                "roles": [{"value": valor, "label": etiqueta} for valor, etiqueta in ROLES_GESTION],
                "areas": list(
                    Area.objects.filter(empresa=empresa).order_by("nombre").values("id", "nombre")
                ),
            }
        )
