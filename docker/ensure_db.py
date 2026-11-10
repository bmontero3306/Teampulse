"""Crea el rol y la base de TeamPulse si todavía no existen, y alinea la clave."""

import os
import sys

import psycopg
from psycopg import sql


def main() -> int:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    database = os.environ["POSTGRES_DB"]
    socket_dir = os.environ.get("PGSOCKET", "/var/run/postgresql")

    with psycopg.connect(
        dbname="postgres",
        user="postgres",
        host=socket_dir,
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
            rol = (
                sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {} SUPERUSER")
                if cur.fetchone()
                else sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} SUPERUSER")
            )
            cur.execute(rol.format(sql.Identifier(user), sql.Literal(password)))

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(database),
                        sql.Identifier(user),
                    )
                )
    print(f">> Base '{database}' lista para el usuario '{user}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
