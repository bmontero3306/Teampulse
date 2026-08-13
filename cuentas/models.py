from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UsuarioQuerySet(models.QuerySet):
    def for_empresa(self, empresa):
        if empresa is None:
            return self.none()
        return self.filter(empresa=empresa)


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        return UsuarioQuerySet(self.model, using=self._db, hints=self._hints)

    def for_empresa(self, empresa):
        return self.get_queryset().for_empresa(empresa)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("rol", Usuario.Rol.EMPLEADO)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("rol", Usuario.Rol.SUPERADMIN)
        extra_fields.setdefault("must_change_password", False)
        extra_fields.setdefault("empresa", None)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        ADMIN_RRHH = "admin_rrhh", "Admin RRHH"
        SUPERVISOR = "supervisor", "Supervisor"
        EMPLEADO = "empleado", "Empleado"

    username = None
    email = models.EmailField("correo electrónico")
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="empresa",
    )
    rol = models.CharField(
        "rol",
        max_length=20,
        choices=Rol.choices,
        default=Rol.EMPLEADO,
    )
    bloqueado = models.BooleanField("bloqueado", default=False)
    must_change_password = models.BooleanField(
        "debe cambiar la contraseña",
        default=True,
    )
    dni = models.CharField("DNI", max_length=20, blank=True)
    puesto = models.ForeignKey(
        "organizacion.Puesto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="puesto",
    )
    area = models.ForeignKey(
        "organizacion.Area",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="área",
    )
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinados",
        verbose_name="supervisor",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "email"],
                name="uniq_usuario_empresa_email",
            ),
        ]

    def __str__(self):
        return self.email
