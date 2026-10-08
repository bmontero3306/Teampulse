# TeamPulse

Sistema de gestión de desempeño (autoevaluación, evaluación de supervisor, firma de conformidad y reportes ISO 9001).

**Stack:** Django 6.1 + Django REST Framework (token) · Angular 22 · Tailwind CSS v4 · SQLite en desarrollo.

La interfaz es la SPA de `frontend/`. Django expone `/api/v1/` y el admin. Las plantillas HTML solo se montan al correr los tests.

Idioma de producto: español. Zona horaria: `America/Argentina/Buenos_Aires`.

## Requisitos

- Python 3.12 o superior (probado con 3.13)
- Node.js 22 o superior (Corepack trae pnpm para `frontend/`)

## Arranque local

```powershell
cd TeamPulse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Opcional: copiá `.env.example` a `.env` y ajustá `SECRET_KEY` / `DEBUG`. Sin `.env` el proyecto arranca con valores de desarrollo.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
```

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

En otra terminal, la SPA (el proxy manda `/api` a Django):

```powershell
cd frontend
corepack pnpm install
corepack pnpm start
```

Abrí [http://localhost:4200/](http://localhost:4200/). El login es `POST /api/v1/auth/login/` y el cliente manda `Authorization: Token …`. El superadmin elige empresa con el header `X-Empresa-Id`.

Para servir la SPA desde Django (como en Render) hace falta el build:

```powershell
cd frontend
corepack pnpm build
```

y después [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

## Datos demo (`seed_demo`)

El comando es idempotente: si los datos ya existen, actualiza claves y no duplica empresas ni usuarios.

Contraseña de **todas** las cuentas demo: `ClaveDemo-2026`  
(`must_change_password=False` para poder recorrer el UAT sin cambio forzado.)

| Email | Rol | Notas |
| --- | --- | --- |
| `admin@teampulse.local` | superadmin | Plataforma; selector de empresa |
| `rrhh@acme.local` | admin_rrhh | Empresa Acme Demo |
| `supervisor@acme.local` | supervisor | Equipo a cargo |
| `empleado1@acme.local` | empleado | Autoevaluación **pendiente** (recorrido UAT) |
| `empleado2@acme.local` | empleado | Autoevaluación ya enviada |
| `empleado3@acme.local` | empleado | Evaluación **cerrada** (comprobante de firma) |
| `rrhh@beta.local` | admin_rrhh | Empresa Beta Demo (aislamiento tenant) |

Estados del ciclo demo en Acme: pendiente de autoevaluación, autoevaluación enviada, autoevaluación en borrador (el propio supervisor) y cerrada.

Si el seed quedó a medias o querés partir de cero:

```powershell
Remove-Item db.sqlite3
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
```

## Superusuario adicional

El identificador es el **email** (no hay username):

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Email sugerido: `admin@teampulse.local` (ya lo crea `seed_demo`). El usuario queda con rol `superadmin`.

## Reportes ISO 9001

Con un usuario `admin_rrhh` o `superadmin` (este último con empresa seleccionada):

1. Entrá a **Reportes ISO** (`/reportes/iso/`).
2. Filtrá por ciclo, área, estado de conformidad o fechas.
3. **Exportar PDF** o **Exportar Excel**. Cada export queda en el audit log.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py test
```

## Recordatorios (cron posterior, sin scheduler)

```powershell
.\.venv\Scripts\python.exe manage.py enviar_recordatorios
.\.venv\Scripts\python.exe manage.py enviar_recordatorios --dry-run
```

Notifica in-app + email (consola en desarrollo) a quienes tienen evaluaciones pendientes en un ciclo activo.

## Demo en Render

El repo incluye `render.yaml`. En el dashboard: **New → Blueprint** y elegí este repo, o creá un **Web Service** a mano:

- **Build:** instala Python y Node, compila `frontend/` y corre `collectstatic` (ver `render.yaml`)
- **Start:** `rm -f db.sqlite3 db.sqlite3-journal && python manage.py migrate --noinput && python manage.py seed_demo && gunicorn teampulse.wsgi:application --bind 0.0.0.0:$PORT --workers 1`
- Env: `PYTHON_VERSION=3.12.8`, `SECRET_KEY` (generada), `DEBUG=False`. `ALLOWED_HOSTS` y CSRF se completan solos con `RENDER_EXTERNAL_HOSTNAME`.

Cada arranque borra el SQLite, migra y vuelve a sembrar las cuentas demo (`ClaveDemo-2026`). En free el disco además es efímero. Un solo worker evita locks de SQLite.

## Producción (fuera del MVP de deploy)

- `DEBUG=False` y `SECRET_KEY` fuerte en `.env`.
- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` con el dominio real (en Render se inyectan solos).
- Cambiar el mailer de consola a SMTP en `MAILERS`.
- `python manage.py collectstatic` hacia `STATIC_ROOT` (WhiteNoise lo sirve detrás de Gunicorn).
- SQLite alcanza para demo; un PostgreSQL queda para una etapa posterior.

## Ayuda in-app

Con sesión iniciada, el menú **Ayuda** (`/ayuda/`) explica el proceso, las piezas del sistema, el flujo de una evaluación y los estados de ciclo/evaluación. Las guías se filtran por rol (un empleado no ve reportes ni auditoría).

## Estructura

- `teampulse/` — settings, URLs raíz
- `app/` — landing, dashboards, seed demo, ayuda in-app
- `cuentas/` — usuario custom, login, roles
- `empresas/` — tenant y suspensión
- `organizacion/` — áreas, puestos, organigrama, competencias
- `evaluaciones/` — plantillas, ciclos y flujo de evaluación
- `notificaciones/` — in-app + email
- `auditoria/` — AuditLog
- `reportes/` — ISO 9001 PDF/Excel
- `theme/` — estáticos y plantillas que todavía usa la suite de tests
- `frontend/` — SPA Angular (auth, shell, módulos de negocio)
- `*/api/` — serializers y vistas DRF bajo `/api/v1/`
