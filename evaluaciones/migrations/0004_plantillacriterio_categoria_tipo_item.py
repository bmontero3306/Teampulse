from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evaluaciones", "0003_evaluacion_comparacion_reunion"),
    ]

    operations = [
        migrations.AddField(
            model_name="plantillacriterio",
            name="categoria",
            field=models.CharField(
                blank=True, default="", max_length=200, verbose_name="categoría"
            ),
        ),
        migrations.AddField(
            model_name="plantillacriterio",
            name="tipo_item",
            field=models.CharField(
                choices=[("escala", "Escala numérica"), ("texto", "Solo texto")],
                default="escala",
                max_length=20,
                verbose_name="tipo de ítem",
            ),
        ),
        migrations.AlterField(
            model_name="plantillacriterio",
            name="comentario_empleado_obligatorio",
            field=models.BooleanField(
                default=True, verbose_name="comentario del empleado obligatorio"
            ),
        ),
        migrations.AlterField(
            model_name="plantillacriterio",
            name="comentario_supervisor_obligatorio",
            field=models.BooleanField(
                default=True, verbose_name="comentario del supervisor obligatorio"
            ),
        ),
    ]
