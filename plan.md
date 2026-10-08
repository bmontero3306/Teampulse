# Plan: templates Django vs Angular

Checklist de los templates de Django para revisar, en una etapa posterior, si cada uno está cubierto en el frontend Angular.

En esta etapa no se analiza ni se modifica código. Cada ítem queda pendiente.

Convención de estado (se completa después):

- `[ ]` pendiente de revisar
- `[x]` cubierto en Angular
- `[~]` cubierto de forma parcial
- `[—]` no aplica a Angular (layout interno, correo, fragmento absorbido por un componente)

Los templates de `frontend/` no entran: ya son Angular.

---

## 1. Layout

- [ ] `theme/templates/base.html` — layout público (login, recuperar clave, home)
- [ ] `theme/templates/app_shell.html` — shell autenticado (menú, selector de empresa, campana)
- [ ] `app/templates/app/ayuda/_layout.html` — layout de las guías de ayuda

## 2. Inicio y panel

- [ ] `app/templates/app/home.html` — portada pública
- [ ] `app/templates/app/dashboard.html` — panel según rol
- [ ] `app/templates/app/partials/_widget_kpis.html` — indicadores del ciclo (admin)
- [ ] `app/templates/app/partials/_widget_pendientes.html` — pendientes del empleado
- [ ] `app/templates/app/partials/_widget_equipo.html` — avance del equipo (supervisor)
- [ ] `app/templates/app/partials/_widget_empresas.html` — listado de empresas (superadmin)
- [ ] `app/templates/app/partials/_empty_state.html` — estado vacío reutilizable

## 3. Cuentas

- [ ] `cuentas/templates/cuentas/login.html` — iniciar sesión
- [ ] `cuentas/templates/cuentas/password_reset.html` — pedir recuperación de contraseña
- [ ] `cuentas/templates/cuentas/password_reset_done.html` — aviso de correo enviado
- [ ] `cuentas/templates/cuentas/password_reset_confirm.html` — elegir nueva contraseña
- [ ] `cuentas/templates/cuentas/password_change.html` — cambio de contraseña autenticado
- [ ] `cuentas/templates/cuentas/perfil.html` — mi perfil
- [ ] `cuentas/templates/cuentas/usuario_lista.html` — listado de usuarios
- [ ] `cuentas/templates/cuentas/usuario_form.html` — alta y edición de usuario
- [ ] `cuentas/templates/cuentas/usuario_confirmar.html` — confirmación de acción sobre usuario
- [ ] `cuentas/templates/cuentas/_campo.html` — campo de formulario con errores
- [ ] `cuentas/templates/cuentas/_mensajes.html` — mensajes de formulario

Correos (no son pantallas de Angular; se listan para no omitirlos):

- [ ] `cuentas/templates/cuentas/password_reset_email.txt`
- [ ] `cuentas/templates/cuentas/password_reset_subject.txt`

## 4. Empresas

- [ ] `empresas/templates/empresas/lista.html` — listado
- [ ] `empresas/templates/empresas/form.html` — alta y edición
- [ ] `empresas/templates/empresas/detalle.html` — detalle
- [ ] `empresas/templates/empresas/confirmar_suspender.html` — confirmar suspensión
- [ ] `empresas/templates/empresas/_badge_estado.html` — badge de estado de empresa
- [ ] `empresas/templates/empresas/_selector_empresa.html` — selector de empresa en el shell

## 5. Organización

- [ ] `organizacion/templates/organizacion/organigrama.html` — organigrama
- [ ] `organizacion/templates/organizacion/_organigrama_nodo.html` — nodo recursivo del árbol
- [ ] `organizacion/templates/organizacion/_nav.html` — navegación interna (organigrama, áreas, puestos, competencias)
- [ ] `organizacion/templates/organizacion/areas_lista.html` — listado de áreas
- [ ] `organizacion/templates/organizacion/area_form.html` — alta y edición de área
- [ ] `organizacion/templates/organizacion/puestos_lista.html` — listado de puestos
- [ ] `organizacion/templates/organizacion/puesto_form.html` — alta y edición de puesto
- [ ] `organizacion/templates/organizacion/competencias_lista.html` — listado de competencias
- [ ] `organizacion/templates/organizacion/competencia_form.html` — alta y edición de competencia

## 6. Evaluaciones: plantillas y ciclos

- [ ] `evaluaciones/templates/evaluaciones/plantillas_lista.html` — listado de plantillas
- [ ] `evaluaciones/templates/evaluaciones/plantilla_form.html` — alta y edición de plantilla (con criterios)
- [ ] `evaluaciones/templates/evaluaciones/_criterio_fila.html` — fila de criterio del formset
- [ ] `evaluaciones/templates/evaluaciones/_badge_tipo.html` — badge de tipo de plantilla
- [ ] `evaluaciones/templates/evaluaciones/ciclos_lista.html` — listado de ciclos
- [ ] `evaluaciones/templates/evaluaciones/ciclo_form.html` — alta de ciclo
- [ ] `evaluaciones/templates/evaluaciones/ciclo_detalle.html` — detalle y acciones del ciclo
- [ ] `evaluaciones/templates/evaluaciones/ciclo_reprogramar.html` — reprogramar fechas
- [ ] `evaluaciones/templates/evaluaciones/ciclo_confirmar.html` — confirmar acción del ciclo (activar, pausar, cancelar, cerrar)
- [ ] `evaluaciones/templates/evaluaciones/_badge_estado.html` — badge de estado (ciclo o evaluación)

## 7. Evaluaciones: flujo

- [ ] `evaluaciones/templates/evaluaciones/mias.html` — mis evaluaciones
- [ ] `evaluaciones/templates/evaluaciones/autoevaluacion.html` — formulario de autoevaluación
- [ ] `evaluaciones/templates/evaluaciones/equipo.html` — equipo a cargo
- [ ] `evaluaciones/templates/evaluaciones/supervisar.html` — evaluación del supervisor
- [ ] `evaluaciones/templates/evaluaciones/resultado.html` — resultado, comparación y conformidad
- [ ] `evaluaciones/templates/evaluaciones/_formulario_items.html` — ítems agrupados del formulario (empleado y supervisor)

## 8. Notificaciones, reportes y auditoría

- [ ] `notificaciones/templates/notificaciones/lista.html` — bandeja de notificaciones
- [ ] `notificaciones/templates/notificaciones/_campana.html` — campana del shell
- [ ] `reportes/templates/reportes/iso.html` — reportes ISO 9001
- [ ] `auditoria/templates/auditoria/lista.html` — listado de auditoría

Correos (no son pantallas de Angular):

- [ ] `notificaciones/templates/notificaciones/email/notificacion.html`
- [ ] `notificaciones/templates/notificaciones/email/notificacion.txt`

## 9. Ayuda

- [ ] `app/templates/app/ayuda/index.html` — índice de ayuda
- [ ] `app/templates/app/ayuda/inicio.html` — Cómo funciona TeamPulse
- [ ] `app/templates/app/ayuda/roles.html` — Roles y permisos
- [ ] `app/templates/app/ayuda/organizacion.html` — Organización
- [ ] `app/templates/app/ayuda/plantillas.html` — Plantillas de evaluación
- [ ] `app/templates/app/ayuda/ciclos.html` — Ciclos de evaluación
- [ ] `app/templates/app/ayuda/flujo.html` — Flujo de una evaluación
- [ ] `app/templates/app/ayuda/conformidad.html` — Firma y conformidad
- [ ] `app/templates/app/ayuda/notificaciones.html` — Notificaciones
- [ ] `app/templates/app/ayuda/reportes.html` — Reportes ISO 9001
- [ ] `app/templates/app/ayuda/auditoria.html` — Auditoría
- [ ] `app/templates/app/ayuda/empresas.html` — Empresas y plataforma
- [ ] `app/templates/app/ayuda/_paso.html` — paso de una guía (estado + texto)

---

## Totales

| Grupo | Cantidad |
| --- | ---: |
| Layout | 3 |
| Inicio y panel | 7 |
| Cuentas (pantallas y fragmentos) | 11 |
| Cuentas (correos) | 2 |
| Empresas | 6 |
| Organización | 9 |
| Plantillas y ciclos | 10 |
| Flujo de evaluación | 6 |
| Notificaciones, reportes y auditoría | 4 |
| Correos de notificación | 2 |
| Ayuda | 13 |
| **Total** | **73** |
