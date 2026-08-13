from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from app.mixins import EmpresaRequiredMixin, RolRequiredMixin
from auditoria.constants import Accion
from auditoria.services import registrar_auditoria
from cuentas.forms import (
    CambioClaveForm,
    LoginForm,
    NuevaClaveForm,
    RecuperarClaveForm,
    UsuarioForm,
)
from cuentas.models import Usuario
from cuentas.services import asignar_clave_temporal
from notificaciones.services import notificar
from organizacion.models import Area


def _url_post_login(user):
    if getattr(user, "rol", None) == Usuario.Rol.SUPERADMIN:
        try:
            return reverse("empresas:lista")
        except NoReverseMatch:
            return "/empresas/"
    return reverse("app:dashboard")


class LoginView(auth_views.LoginView):
    template_name = "cuentas/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return _url_post_login(self.request.user)


class LogoutView(auth_views.LogoutView):
    next_page = "/"
    http_method_names = ["post", "options"]


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "cuentas/password_reset.html"
    email_template_name = "cuentas/password_reset_email.txt"
    subject_template_name = "cuentas/password_reset_subject.txt"
    form_class = RecuperarClaveForm
    success_url = reverse_lazy("cuentas:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "cuentas/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "cuentas/password_reset_confirm.html"
    form_class = NuevaClaveForm
    success_url = reverse_lazy("cuentas:login")

    def form_valid(self, form):
        form.user.must_change_password = False
        messages.success(
            self.request,
            "Tu contraseña se actualizó. Ya podés iniciar sesión.",
        )
        return super().form_valid(form)


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "cuentas/password_change.html"
    form_class = CambioClaveForm

    def form_valid(self, form):
        form.user.must_change_password = False
        messages.success(self.request, "Tu contraseña se actualizó correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return _url_post_login(self.request.user)


class PerfilView(LoginRequiredMixin, TemplateView):
    template_name = "cuentas/perfil.html"


class UsuarioGestionMixin(RolRequiredMixin, EmpresaRequiredMixin):
    model = Usuario
    roles_permitidos = [Usuario.Rol.SUPERADMIN, Usuario.Rol.ADMIN_RRHH]

    def get_queryset(self):
        return Usuario.objects.for_empresa(self.request.empresa).select_related(
            "area",
            "puesto",
            "supervisor",
        )


class UsuarioListView(UsuarioGestionMixin, ListView):
    template_name = "cuentas/usuario_lista.html"
    context_object_name = "usuarios"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().order_by("last_name", "first_name", "email")
        rol = self.request.GET.get("rol")
        if rol:
            qs = qs.filter(rol=rol)
        activo = self.request.GET.get("activo")
        if activo == "1":
            qs = qs.filter(is_active=True)
        elif activo == "0":
            qs = qs.filter(is_active=False)
        area = self.request.GET.get("area")
        if area:
            qs = qs.filter(area_id=area)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Usuario.Rol.choices
        context["filtro_rol"] = self.request.GET.get("rol", "")
        context["filtro_activo"] = self.request.GET.get("activo", "")
        context["filtro_area"] = self.request.GET.get("area", "")
        context["areas"] = Area.objects.filter(empresa=self.request.empresa).order_by("nombre")
        return context


class UsuarioFormMixin(UsuarioGestionMixin):
    form_class = UsuarioForm
    template_name = "cuentas/usuario_form.html"
    success_url = reverse_lazy("cuentas:usuarios")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.empresa
        return kwargs


class UsuarioCreateView(UsuarioFormMixin, CreateView):
    def form_valid(self, form):
        form.instance.empresa = self.request.empresa
        form.instance.must_change_password = True
        clave = asignar_clave_temporal(form.instance)
        self.object = form.save()
        registrar_auditoria(self.request, Accion.CREAR, instance=self.object)
        notificar(
            tipo="usuario_creado",
            usuario=self.object,
            titulo="Tu cuenta fue creada",
            mensaje="Se creó tu usuario en TeamPulse. Debés cambiar la contraseña al ingresar.",
            url="/cuentas/perfil/",
            empresa=self.object.empresa,
        )
        messages.success(
            self.request,
            f"Usuario creado. Se envió notificación al usuario. Contraseña temporal: {clave}",
        )
        return redirect("cuentas:usuarios")


class UsuarioUpdateView(UsuarioFormMixin, UpdateView):
    def form_valid(self, form):
        self.object = form.save()
        notificar(
            tipo="usuario_modificado",
            usuario=self.object,
            titulo="Tus datos fueron actualizados",
            mensaje="Se modificaron los datos de tu cuenta en TeamPulse.",
            url="/cuentas/perfil/",
            empresa=self.object.empresa,
        )
        messages.success(
            self.request,
            "Usuario actualizado. Se envió notificación al usuario.",
        )
        return redirect("cuentas:usuarios")


class UsuarioAccionMixin(UsuarioGestionMixin, DetailView):
    template_name = "cuentas/usuario_confirmar.html"
    context_object_name = "objetivo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.accion_contexto())
        return context

    def accion_contexto(self):
        raise NotImplementedError

    def ejecutar(self, usuario):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            messages.error(request, "No podés aplicar esta acción sobre tu propia cuenta.")
            return redirect("cuentas:usuarios")
        self.ejecutar(usuario)
        return redirect("cuentas:usuarios")


class UsuarioDesactivarView(UsuarioAccionMixin):
    def accion_contexto(self):
        return {
            "titulo": "Desactivar usuario",
            "mensaje": f"¿Desactivar a {self.object}? No podrá iniciar sesión.",
            "confirmacion": "Desactivar",
            "peligro": True,
        }

    def ejecutar(self, usuario):
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        notificar(
            tipo="usuario_desactivado",
            usuario=usuario,
            titulo="Tu cuenta fue desactivada",
            mensaje="Tu usuario en TeamPulse fue desactivado.",
            url="/cuentas/login/",
            empresa=usuario.empresa,
        )
        messages.success(self.request, "Usuario desactivado. Se envió notificación al usuario.")


class UsuarioBloquearView(UsuarioAccionMixin):
    def accion_contexto(self):
        return {
            "titulo": "Bloquear usuario",
            "mensaje": f"¿Bloquear a {self.object}? No podrá iniciar sesión hasta que se desbloquee.",
            "confirmacion": "Bloquear",
            "peligro": True,
        }

    def ejecutar(self, usuario):
        usuario.bloqueado = True
        usuario.save(update_fields=["bloqueado"])
        notificar(
            tipo="usuario_bloqueado",
            usuario=usuario,
            titulo="Tu cuenta fue bloqueada",
            mensaje="Tu usuario en TeamPulse fue bloqueado. Contactá a RRHH.",
            url="/cuentas/login/",
            empresa=usuario.empresa,
        )
        messages.success(self.request, "Usuario bloqueado. Se envió notificación al usuario.")


class UsuarioResetClaveView(UsuarioAccionMixin):
    def accion_contexto(self):
        return {
            "titulo": "Restablecer contraseña",
            "mensaje": f"¿Generar una contraseña temporal para {self.object}?",
            "confirmacion": "Restablecer clave",
            "peligro": False,
        }

    def ejecutar(self, usuario):
        clave = asignar_clave_temporal(usuario)
        usuario.save(update_fields=["password", "must_change_password"])
        notificar(
            tipo="usuario_reset_clave",
            usuario=usuario,
            titulo="Se restableció tu contraseña",
            mensaje="Tu contraseña fue restablecida. Vas a tener que cambiarla al ingresar.",
            url="/cuentas/clave/",
            empresa=usuario.empresa,
        )
        messages.success(
            self.request,
            f"Se restableció la clave. Se envió notificación al usuario. Contraseña temporal: {clave}",
        )
