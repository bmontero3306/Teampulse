#!/bin/bash
# Arranca PostgreSQL en este mismo contenedor, migra y siembra solo la primera vez.
set -euo pipefail

export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-teampulse}"
export POSTGRES_USER="${POSTGRES_USER:-teampulse}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-teampulse}"
export POSTGRES_SSLMODE="${POSTGRES_SSLMODE:-disable}"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export DEBUG="${DEBUG:-False}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-*}"
export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

PG_BIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -n 1)"
APP_PID=""

ident_ok() {
  [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]
}

if ! ident_ok "$POSTGRES_DB" || ! ident_ok "$POSTGRES_USER"; then
  echo "POSTGRES_DB y POSTGRES_USER solo pueden tener letras, números y _." >&2
  exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
  echo "POSTGRES_PASSWORD no puede estar vacía." >&2
  exit 1
fi

stop_postgres() {
  if [ -d "$PGDATA" ] && [ -s "$PGDATA/PG_VERSION" ]; then
    su -s /bin/bash postgres -c "$PG_BIN/pg_ctl -D '$PGDATA' -m fast -w stop" >/dev/null 2>&1 || true
  fi
}

dump_pg_log() {
  if [ -f "$PGDATA/postgresql.log" ]; then
    echo "----- postgresql.log -----" >&2
    tail -n 80 "$PGDATA/postgresql.log" >&2 || true
  fi
}

start_postgres() {
  mkdir -p "$PGDATA" /var/run/postgresql
  chown -R postgres:postgres "$PGDATA" /var/run/postgresql
  chmod 700 "$PGDATA"
  chmod 775 /var/run/postgresql

  if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo ">> Inicializando PostgreSQL en $PGDATA"
    su -s /bin/bash postgres -c \
      "$PG_BIN/initdb -D '$PGDATA' --encoding=UTF8 --locale=C.UTF-8 --auth-local=trust --auth-host=scram-sha-256 --username=postgres"
    cat >> "$PGDATA/postgresql.conf" <<'EOF'
listen_addresses = '127.0.0.1'
unix_socket_directories = '/var/run/postgresql'
shared_buffers = 32MB
max_connections = 50
EOF
  else
    echo ">> PostgreSQL ya tiene datos en $PGDATA"
  fi

  echo ">> Levantando PostgreSQL"
  if ! su -s /bin/bash postgres -c "$PG_BIN/pg_ctl -D '$PGDATA' -w -l '$PGDATA/postgresql.log' start"; then
    dump_pg_log
    exit 1
  fi

  python /app/docker/ensure_db.py
}

shutdown() {
  if [ -n "$APP_PID" ]; then
    kill -TERM "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
    APP_PID=""
  fi
  stop_postgres
}

trap shutdown EXIT
trap 'exit 0' TERM INT

start_postgres

cd /app
echo ">> Migraciones"
python manage.py migrate --noinput
echo ">> Seed (solo si esta base todavía no fue sembrada)"
python /app/docker/seed_if_needed.py

echo ">> TeamPulse en http://0.0.0.0:8000"
"$@" &
APP_PID=$!
set +e
wait "$APP_PID"
code=$?
set -e
APP_PID=""
stop_postgres
exit "$code"
