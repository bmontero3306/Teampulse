from django.core.management.base import BaseCommand

from app.seed import CUENTAS_DEMO, DEMO_PASSWORD, seed_demo


class Command(BaseCommand):
    help = (
        "Carga datos demo para UAT: 2 empresas, roles, plantilla mixta y ciclo activo. "
        "Se puede re-ejecutar: actualiza claves y no duplica."
    )

    def handle(self, *args, **options):
        seed_demo(stdout=self.stdout)
        self.stdout.write("")
        self.stdout.write("Cuentas demo (misma contraseña para todas):")
        self.stdout.write(f"  Contraseña: {DEMO_PASSWORD}")
        for email, rol, nota in CUENTAS_DEMO:
            self.stdout.write(f"  {email:28}  {rol:12}  {nota}")
        self.stdout.write(
            self.style.SUCCESS("seed_demo finalizó. must_change_password=False.")
        )
