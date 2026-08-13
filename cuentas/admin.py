from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from cuentas.models import Usuario


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email",)


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    model = Usuario
    list_display = (
        "email",
        "first_name",
        "last_name",
        "empresa",
        "rol",
        "area",
        "puesto",
        "is_active",
        "bloqueado",
    )
    list_filter = ("empresa", "rol", "is_active", "bloqueado")
    search_fields = ("email", "first_name", "last_name", "dni")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "dni")}),
        (
            "Empresa y rol",
            {
                "fields": (
                    "empresa",
                    "rol",
                    "area",
                    "puesto",
                    "supervisor",
                    "bloqueado",
                    "must_change_password",
                )
            },
        ),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "empresa", "rol"),
            },
        ),
    )
