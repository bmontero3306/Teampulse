import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cuentas", "0001_initial"),
        ("empresas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("accion", models.CharField(max_length=64, verbose_name="acción")),
                (
                    "modelo",
                    models.CharField(blank=True, max_length=128, verbose_name="modelo"),
                ),
                (
                    "object_id",
                    models.CharField(
                        blank=True, max_length=64, verbose_name="id de objeto"
                    ),
                ),
                (
                    "payload",
                    models.JSONField(blank=True, default=dict, verbose_name="payload"),
                ),
                (
                    "ip",
                    models.GenericIPAddressField(
                        blank=True, null=True, verbose_name="IP"
                    ),
                ),
                (
                    "user_agent",
                    models.CharField(
                        blank=True, max_length=512, verbose_name="agente de usuario"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="creado"),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="empresas.empresa",
                        verbose_name="empresa",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="cuentas.usuario",
                        verbose_name="usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "registro de auditoría",
                "verbose_name_plural": "registros de auditoría",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["empresa", "created_at"],
                name="auditoria_empresa_fecha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["modelo", "object_id"],
                name="auditoria_modelo_objeto_idx",
            ),
        ),
    ]
