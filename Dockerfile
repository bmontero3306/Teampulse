# TeamPulse: Angular (build) + Django/Gunicorn + PostgreSQL en una sola imagen.
# La base se inicializa en el primer arranque y los datos viven en /var/lib/postgresql/data.

FROM node:22-bookworm-slim AS frontend

WORKDIR /src
RUN corepack enable && corepack prepare pnpm@10.34.6 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.dangerouslyAllowAllBuilds=true

COPY frontend/ ./
RUN pnpm build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PGDATA=/var/lib/postgresql/data \
    DEBUG=False

RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        postgresql \
        postgresql-contrib \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/lib/postgresql/data /var/run/postgresql \
    && chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql \
    && chmod 775 /var/run/postgresql

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /src/dist/teampulse/browser /app/frontend/dist/teampulse/browser

RUN python manage.py collectstatic --noinput \
    && rm -f /app/db.sqlite3 \
    && sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000
VOLUME ["/var/lib/postgresql/data"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "teampulse.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
