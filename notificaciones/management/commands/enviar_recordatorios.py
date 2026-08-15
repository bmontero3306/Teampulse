from django.core.management.base import BaseCommand
from django.urls import reverse

from notificaciones.events import RECORDATORIO_VENCIMIENTO
from notificaciones.services import notificar


class Command(BaseCommand):
    help = (
        "Envía recordatorios de vencimiento a participantes con pendientes. "
        "Pensado para cron; no incluye scheduler."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista destinatarios sin enviar.",
        )

    def handle(self, *args, **options):
        destinatarios = list(self._participantes_pendientes())
        if options["dry_run"]:
            self.stdout.write(f"{len(destinatarios)} recordatorio(s) pendiente(s).")
            return
        enviados = 0
        for usuario, empresa, contexto in destinatarios:
            notificar(
                tipo=RECORDATORIO_VENCIMIENTO,
                usuario=usuario,
                empresa=empresa,
                contexto=contexto,
            )
            enviados += 1
        self.stdout.write(self.style.SUCCESS(f"{enviados} recordatorio(s) enviado(s)."))

    def _participantes_pendientes(self):
        try:
            from evaluaciones.models import CicloEvaluacion, Evaluacion
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    "El módulo de evaluaciones aún no está disponible (WP5)."
                )
            )
            return []

        pendientes_auto = (
            Evaluacion.Estado.PENDIENTE_AUTO,
            Evaluacion.Estado.AUTO_BORRADOR,
        )
        pendientes_supervisor = (
            Evaluacion.Estado.AUTO_COMPLETA,
            Evaluacion.Estado.SUPERVISOR_BORRADOR,
        )
        pendientes_reunion = (Evaluacion.Estado.PENDIENTE_COMPARACION,)
        pendientes_firma = (Evaluacion.Estado.PENDIENTE_CONFORMIDAD,)
        estados = (
            pendientes_auto
            + pendientes_supervisor
            + pendientes_reunion
            + pendientes_firma
        )

        qs = (
            Evaluacion.objects.filter(
                ciclo__estado=CicloEvaluacion.Estado.ACTIVO,
                estado__in=estados,
            )
            .select_related("evaluado", "evaluador", "ciclo", "empresa")
            .order_by("pk")
        )

        vistos = set()
        resultado = []
        for evaluacion in qs:
            if evaluacion.estado in pendientes_auto:
                usuario = evaluacion.evaluado
                url = reverse("evaluaciones:auto", args=[evaluacion.pk])
            elif evaluacion.estado in pendientes_supervisor:
                usuario = evaluacion.evaluador
                url = reverse("evaluaciones:supervisar", args=[evaluacion.pk])
            elif evaluacion.estado in pendientes_reunion:
                usuario = evaluacion.evaluador
                url = reverse("evaluaciones:resultado", args=[evaluacion.pk])
            else:
                usuario = evaluacion.evaluado
                url = reverse("evaluaciones:resultado", args=[evaluacion.pk])
            if usuario is None:
                continue
            clave = (usuario.pk, evaluacion.ciclo_id)
            if clave in vistos:
                continue
            vistos.add(clave)
            fecha = ""
            if evaluacion.ciclo.fecha_cierre:
                fecha = evaluacion.ciclo.fecha_cierre.strftime("%d/%m/%Y")
            resultado.append(
                (
                    usuario,
                    evaluacion.empresa,
                    {
                        "ciclo": evaluacion.ciclo.nombre,
                        "fecha_cierre": fecha,
                        "url": url,
                        "evaluado": evaluacion.evaluado.get_full_name()
                        or evaluacion.evaluado.email,
                    },
                )
            )
        return resultado
