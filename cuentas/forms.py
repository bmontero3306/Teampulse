from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.core.exceptions import ValidationError

from app.forms_widgets import INPUT_CSS, SELECT_CSS
from cuentas.models import Usuario
from cuentas.services import sincronizar_supervisor
from empresas.models import Empresa
from organizacion.models import Area, Puesto

ROLES_GESTION = [
    (Usuario.Rol.ADMIN_RRHH, "Admin RRHH"),
    (Usuario.Rol.SUPERVISOR, "Supervisor"),
    (Usuario.Rol.EMPLEADO, "Empleado"),
]


def _aplicar_css(campos, css=INPUT_CSS):
    for campo in campos:
        existing = campo.widget.attrs.get("class", "")
        campo.widget.attrs["class"] = f"{existing} {css}".strip()


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Email o contraseña incorrectos.",
        "inactive": "Tu cuenta está desactivada.",
        "bloqueado": "Tu cuenta está bloqueada. Contactá a RRHH.",
        "empresa_suspendida": "La empresa está suspendida. No podés iniciar sesión.",
        "empresa_inactiva": "La empresa no está activa. No podés iniciar sesión.",
        "sin_empresa": "Tu cuenta no está asociada a una empresa.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Correo electrónico"
        self.fields["username"].widget = forms.EmailInput(
            attrs={
                "class": INPUT_CSS,
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "tu@empresa.com",
            }
        )
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update(
            {
                "class": INPUT_CSS,
                "autocomplete": "current-password",
                "placeholder": "••••••••",
            }
        )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )
        if getattr(user, "bloqueado", False):
            raise ValidationError(
                self.error_messages["bloqueado"],
                code="bloqueado",
            )
        if getattr(user, "rol", None) == Usuario.Rol.SUPERADMIN:
            return
        empresa = getattr(user, "empresa", None)
        if empresa is None:
            raise ValidationError(
                self.error_messages["sin_empresa"],
                code="sin_empresa",
            )
        if empresa.estado == Empresa.Estado.SUSPENDIDA:
            raise ValidationError(
                self.error_messages["empresa_suspendida"],
                code="empresa_suspendida",
            )
        if empresa.estado != Empresa.Estado.ACTIVA:
            raise ValidationError(
                self.error_messages["empresa_inactiva"],
                code="empresa_inactiva",
            )


class RecuperarClaveForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Correo electrónico"
        self.fields["email"].widget.attrs.update(
            {
                "class": INPUT_CSS,
                "autocomplete": "email",
                "placeholder": "tu@empresa.com",
            }
        )

    def get_users(self, email):
        usuarios = Usuario.objects.filter(
            email__iexact=email,
            is_active=True,
            bloqueado=False,
        ).select_related("empresa")
        for usuario in usuarios:
            if not usuario.has_usable_password():
                continue
            if usuario.rol == Usuario.Rol.SUPERADMIN:
                yield usuario
                continue
            empresa = usuario.empresa
            if empresa is not None and empresa.estado == Empresa.Estado.ACTIVA:
                yield usuario


class NuevaClaveForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_css(self.fields.values())
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"


class CambioClaveForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_css(self.fields.values())
        self.fields["old_password"].widget.attrs["autocomplete"] = "current-password"
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"


class UsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=ROLES_GESTION, label="Rol")

    class Meta:
        model = Usuario
        fields = (
            "first_name",
            "last_name",
            "email",
            "dni",
            "rol",
            "area",
            "puesto",
            "supervisor",
            "is_active",
            "bloqueado",
        )
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "dni": "DNI",
            "area": "Área",
            "puesto": "Puesto",
            "supervisor": "Supervisor",
            "is_active": "Activo",
            "bloqueado": "Bloqueado",
        }
        help_texts = {
            "supervisor": "Si el puesto tiene superior, el supervisor se completa automáticamente.",
            "is_active": "Desmarcado, la persona no puede iniciar sesión.",
            "bloqueado": "Una cuenta bloqueada no puede iniciar sesión aunque esté activa.",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa or getattr(self.instance, "empresa", None)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True

        if not self.instance.pk:
            self.fields.pop("is_active", None)
            self.fields.pop("bloqueado", None)

        areas = Area.objects.none()
        puestos = Puesto.objects.none()
        supervisores = Usuario.objects.none()
        if self.empresa is not None:
            areas = Area.objects.filter(empresa=self.empresa)
            puestos = Puesto.objects.filter(empresa=self.empresa)
            supervisores = Usuario.objects.for_empresa(self.empresa).filter(is_active=True)
            if self.instance.pk:
                supervisores = supervisores.exclude(pk=self.instance.pk)
            else:
                areas = areas.filter(activa=True)
                puestos = puestos.filter(activo=True)

        self.fields["area"].queryset = areas
        self.fields["area"].required = False
        self.fields["puesto"].queryset = puestos
        self.fields["puesto"].required = False
        self.fields["supervisor"].queryset = supervisores
        self.fields["supervisor"].required = False

        for nombre, campo in self.fields.items():
            if isinstance(campo.widget, forms.CheckboxInput):
                continue
            css = SELECT_CSS if isinstance(campo.widget, forms.Select) else INPUT_CSS
            campo.widget.attrs["class"] = css

        self.mapa_puesto_supervisor = self._armar_mapa_supervisor()

    def _armar_mapa_supervisor(self):
        if self.empresa is None:
            return {}
        ocupantes = {
            usuario.puesto_id: usuario.pk
            for usuario in Usuario.objects.filter(
                empresa=self.empresa,
                puesto__isnull=False,
                is_active=True,
            )
        }
        mapa = {}
        for puesto in Puesto.objects.filter(empresa=self.empresa):
            superior_id = puesto.puesto_superior_id
            if superior_id and superior_id in ocupantes:
                mapa[str(puesto.pk)] = ocupantes[superior_id]
        return mapa

    def clean_email(self):
        email = Usuario.objects.normalize_email(self.cleaned_data["email"])
        if self.empresa is None:
            return email
        qs = Usuario.objects.filter(empresa=self.empresa, email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un usuario con este correo en la empresa.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.empresa is not None and usuario.empresa_id is None:
            usuario.empresa = self.empresa
        sincronizar_supervisor(usuario)
        if commit:
            usuario.save()
        return usuario
