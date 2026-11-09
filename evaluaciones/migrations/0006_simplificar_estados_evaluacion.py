from django.db import migrations, models


def _remap(apps, mapa):
    Evaluacion = apps.get_model("evaluaciones", "Evaluacion")
    for viejo, nuevo in mapa.items():
        Evaluacion.objects.filter(estado=viejo).update(estado=nuevo)


def forwards(apps, schema_editor):
    _remap(
        apps,
        {
            "pendiente_auto": "autoevaluacion",
            "auto_borrador": "autoevaluacion",
            "auto_completa": "evaluacion_supervisor",
            "supervisor_borrador": "evaluacion_supervisor",
            "pendiente_comparacion": "pendiente_reunion",
            "cerrada_con_obs": "cerrada",
        },
    )


def backwards(apps, schema_editor):
    _remap(
        apps,
        {
            "autoevaluacion": "pendiente_auto",
            "evaluacion_supervisor": "auto_completa",
            "pendiente_reunion": "pendiente_comparacion",
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("evaluaciones", "0005_alter_plantillacriterio_categoria"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="evaluacion",
            name="estado",
            field=models.CharField(
                choices=[
                    ("autoevaluacion", "Autoevaluación"),
                    ("evaluacion_supervisor", "Evaluación del supervisor"),
                    ("pendiente_reunion", "Pendiente de reunión"),
                    ("pendiente_conformidad", "Pendiente de conformidad"),
                    ("cerrada", "Cerrada"),
                ],
                default="autoevaluacion",
                max_length=30,
                verbose_name="estado",
            ),
        ),
    ]
