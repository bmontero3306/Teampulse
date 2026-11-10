"""Corre seed_demo la primera vez que la base está vacía de siembra.

El marcador queda en PostgreSQL, así un reinicio del contenedor no vuelve a
pisar claves ni evaluaciones. Si el seed falla a mitad de camino, no se marca
y el próximo arranque lo reintenta (seed_demo es idempotente).
"""

import os
import sys


def _forzar() -> bool:
    return os.environ.get("FORCE_SEED", "").strip().lower() in {
        "1",
        "true",
        "t",
        "yes",
        "si",
        "sí",
    }


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teampulse.settings")
    import django

    django.setup()

    from django.core.management import call_command
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS teampulse_seed_marker (
                id boolean PRIMARY KEY DEFAULT TRUE CHECK (id),
                seeded_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute("SELECT 1 FROM teampulse_seed_marker LIMIT 1")
        ya_sembrada = cursor.fetchone() is not None

    if ya_sembrada and not _forzar():
        print(">> Seed omitido: esta base ya tiene los datos iniciales.")
        return 0

    if ya_sembrada:
        print(">> FORCE_SEED activo: se vuelve a ejecutar seed_demo.")
    else:
        print(">> Primera carga: ejecutando seed_demo...")

    call_command("seed_demo")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO teampulse_seed_marker (id)
            VALUES (TRUE)
            ON CONFLICT (id) DO UPDATE SET seeded_at = now()
            """
        )
    print(">> Seed registrado. Los próximos arranques no lo vuelven a correr.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
