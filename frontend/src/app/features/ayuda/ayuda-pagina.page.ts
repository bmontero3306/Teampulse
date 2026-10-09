import { Component, computed, effect, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { AyudaBadgeComponent } from './ayuda-badge.component';
import { paginaPorSlug, paginasVisibles } from './ayuda.catalogo';
import { AyudaPasoComponent } from './ayuda-paso.component';

/**
 * Contenido de cada guía (bloque ayuda_content).
 * El aside y la navegación anterior/siguiente están en ayuda-layout.ts
 * (equivalente de _layout.html, a cargo de otro agente).
 */
@Component({
  selector: 'app-ayuda-guia',
  imports: [RouterLink, AyudaPasoComponent, AyudaBadgeComponent],
  template: `
    @if (estado() === 'ok') {
      @switch (slug()) {
            @case ('inicio') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Empezar</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Cómo funciona TeamPulse</h1>
                <p class="mt-2 text-sm text-slate-600">
                  TeamPulse gestiona el desempeño por empresa: autoevaluación, evaluación del supervisor, firma de
                  conformidad y reportes alineados a ISO 9001.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">El proceso, en orden</h2>
                  <ol class="mt-3 space-y-3">
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">1. Armar la organización</p>
                      <p class="mt-1 text-slate-600">
                        Áreas, puestos, organigrama y competencias. Cada persona tiene un puesto y, si aplica, un
                        supervisor.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">2. Definir qué se evalúa</p>
                      <p class="mt-1 text-slate-600">
                        Una plantilla reúne criterios (competencias), escalas y ponderaciones. Se puede asociar a
                        puestos.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">3. Abrir un ciclo</p>
                      <p class="mt-1 text-slate-600">
                        RRHH crea un ciclo con fechas y plantilla por defecto. Al activarlo se generan las evaluaciones
                        de quienes tienen puesto.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">4. Recorrer el flujo</p>
                      <p class="mt-1 text-slate-600">
                        Empleado autoevalúa → supervisor evalúa → (opcional) reunión de feedback → el empleado firma
                        conformidad o deja observación.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">5. Cerrar y reportar</p>
                      <p class="mt-1 text-slate-600">
                        El ciclo se cierra. RRHH exporta reportes ISO y consulta la auditoría de lo ocurrido.
                      </p>
                    </li>
                  </ol>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Qué hay en el sistema</h2>
                  <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white">
                    <table class="min-w-full text-left">
                      <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                        <tr>
                          <th class="px-4 py-3 font-medium">Pieza</th>
                          <th class="px-4 py-3 font-medium">Para qué sirve</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Empresa</td>
                          <td class="px-4 py-3">Tenant: aísla usuarios, evaluaciones y reportes.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Área y puesto</td>
                          <td class="px-4 py-3">
                            Estructura. El puesto define plantilla y, si no hay supervisor directo, el evaluador.
                          </td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Competencia</td>
                          <td class="px-4 py-3">Lo que se mide: técnica, actitudinal, objetivo u otra.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Plantilla</td>
                          <td class="px-4 py-3">Criterios + escalas + ponderación. Se puede duplicar.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Ciclo</td>
                          <td class="px-4 py-3">Ventana de tiempo. Solo uno activo por empresa.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Evaluación</td>
                          <td class="px-4 py-3">Una por persona y ciclo. Recorre estados hasta el cierre.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Notificación</td>
                          <td class="px-4 py-3">Aviso in-app y email cuando cambia el flujo.</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Auditoría</td>
                          <td class="px-4 py-3">Registro de altas, cambios, firmas y exportaciones.</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                <section class="rounded-xl border border-sky-200 bg-sky-50 p-4">
                  <p class="font-medium text-sky-900">Por dónde seguir</p>
                  <p class="mt-1 text-sky-800">
                    Si vas a completar una evaluación, leé
                    <a routerLink="/ayuda/flujo" class="font-medium underline">Flujo de una evaluación</a>.
                    @if (muestraConfig()) {
                      Si armás el proceso desde RRHH, empezá por
                      <a routerLink="/ayuda/organizacion" class="font-medium underline">Organización</a>
                      y después
                      <a routerLink="/ayuda/ciclos" class="font-medium underline">Ciclos</a>.
                    }
                  </p>
                </section>
              </div>
            }
            @case ('roles') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Empezar</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Roles y permisos</h1>
                <p class="mt-2 text-sm text-slate-600">
                  El menú y las pantallas se arman según el rol. Un supervisor también es evaluado: ve «Equipo» y «Mis
                  evaluaciones».
                </p>
              </header>

              <div class="space-y-6 text-sm text-slate-700">
                <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                  <table class="min-w-full text-left">
                    <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                      <tr>
                        <th class="px-4 py-3 font-medium">Rol</th>
                        <th class="px-4 py-3 font-medium">Qué hace</th>
                        <th class="px-4 py-3 font-medium">Qué ve</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr>
                        <td class="px-4 py-3 font-medium text-slate-900">Empleado</td>
                        <td class="px-4 py-3">Completa la autoevaluación y firma (o observa) la conformidad.</td>
                        <td class="px-4 py-3">Panel, Mis evaluaciones, Notificaciones, Perfil, Ayuda.</td>
                      </tr>
                      <tr>
                        <td class="px-4 py-3 font-medium text-slate-900">Supervisor</td>
                        <td class="px-4 py-3">
                          Evalúa a su equipo, registra o omite la reunión de feedback y también se autoevalúa.
                        </td>
                        <td class="px-4 py-3">Lo del empleado más Organigrama, Plantillas, Ciclos y Equipo.</td>
                      </tr>
                      <tr>
                        <td class="px-4 py-3 font-medium text-slate-900">Admin RRHH</td>
                        <td class="px-4 py-3">
                          Configura la empresa: usuarios, organización, plantillas, ciclos, reportes y auditoría. Puede
                          asignar un evaluador si faltó.
                        </td>
                        <td class="px-4 py-3">Usuarios, Organigrama, Plantillas, Ciclos, Reportes ISO, Auditoría.</td>
                      </tr>
                      <tr>
                        <td class="px-4 py-3 font-medium text-slate-900">Superadmin</td>
                        <td class="px-4 py-3">
                          Administra empresas de la plataforma. Con una empresa seleccionada, opera como RRHH de ese
                          tenant.
                        </td>
                        <td class="px-4 py-3">Empresas siempre; el resto cuando hay empresa en contexto.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Reglas que conviene tener presentes</h2>
                  <ul class="mt-2 list-disc space-y-1 pl-5 text-slate-600">
                    <li>
                      El identificador de login es el <strong class="font-medium text-slate-800">email</strong>, no un
                      username.
                    </li>
                    <li>Los datos están aislados por empresa: no se mezclan evaluaciones ni usuarios entre tenants.</li>
                    <li>Si la empresa está suspendida o inactiva, sus usuarios no pueden iniciar sesión.</li>
                    <li>Un usuario nuevo puede tener que cambiar la contraseña en el primer acceso.</li>
                    <li>Áreas, puestos y competencias no se borran: se desactivan.</li>
                  </ul>
                </section>
              </div>
            }
            @case ('organizacion') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Configuración</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Organización</h1>
                <p class="mt-2 text-sm text-slate-600">
                  La estructura de la empresa determina quién evalúa a quién y con qué plantilla.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Áreas</h2>
                  <p class="mt-2 text-slate-600">
                    Pueden anidarse (área padre). Un área no puede ser padre de sí misma ni generar un ciclo. El padre
                    tiene que ser de la misma empresa. Al «eliminar» se marca como inactiva.
                  </p>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Puestos</h2>
                  <p class="mt-2 text-slate-600">
                    Cada puesto pertenece a un área (opcional) y puede tener un puesto superior. Esa jerarquía se usa
                    como respaldo para resolver el evaluador si la persona no tiene supervisor asignado. Las
                    competencias y ponderaciones no se cargan en el puesto: al evaluar se usa la plantilla asociada (o
                    la plantilla por defecto del ciclo).
                  </p>
                  <div class="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                    <p class="font-medium text-slate-900">Cómo se elige el evaluador al activar el ciclo</p>
                    <ol class="mt-2 list-decimal space-y-1 pl-5 text-slate-600">
                      <li>
                        Primero se usa el <strong class="font-medium text-slate-800">supervisor</strong> del usuario, si
                        está activo y no bloqueado.
                      </li>
                      <li>
                        Si no hay, se busca quién ocupa el
                        <strong class="font-medium text-slate-800">puesto superior</strong>.
                      </li>
                      <li>
                        Si tampoco hay, la evaluación queda marcada
                        <strong class="font-medium text-slate-800">sin evaluador</strong> y RRHH la asigna a mano.
                      </li>
                    </ol>
                  </div>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Competencias</h2>
                  <p class="mt-2 text-slate-600">
                    Tipos: técnica, actitudinal, objetivo u otra. Son el catálogo: cada criterio de una plantilla apunta
                    a una competencia, con su escala y ponderación.
                  </p>
                </section>

                <section class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
                  <p class="font-medium">Antes de activar un ciclo</p>
                  <p class="mt-1">
                    Toda persona que deba evaluarse necesita un <strong>puesto</strong> asignado. Si el ciclo filtra por
                    áreas, solo participan quienes están en esas áreas.
                  </p>
                </section>
              </div>
            }
            @case ('plantillas') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Configuración</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Plantillas de evaluación</h1>
                <p class="mt-2 text-sm text-slate-600">
                  La plantilla es el formulario que van a completar empleado y supervisor. Se puede duplicar para no
                  arrancar de cero.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Qué incluye</h2>
                  <ul class="mt-3 list-disc space-y-2 pl-5 text-slate-600">
                    <li><strong class="font-medium text-slate-800">Tipo:</strong> técnica, actitudinal, objetivos o mixta.</li>
                    <li>
                      <strong class="font-medium text-slate-800">Criterios:</strong> se agregan con un formulario. Cada
                      uno apunta a una competencia (del catálogo o creada ahí), con orden, escala (mín–máx) y
                      ponderación.
                    </li>
                    <li>
                      <strong class="font-medium text-slate-800">Categorías:</strong> nombre libre para agrupar el
                      formulario (p. ej. Competencias generales, Desempeño técnico, Cierre).
                    </li>
                    <li>
                      <strong class="font-medium text-slate-800">Tipo de ítem:</strong> escala numérica (puntaje +
                      devolución) o solo texto (devolución, sin puntaje ni ponderación).
                    </li>
                    <li>
                      <strong class="font-medium text-slate-800">Devolución:</strong> comentario escrito por ítem. Se
                      puede exigir al empleado y/o al supervisor. En criterios nuevos viene marcada como obligatoria.
                    </li>
                    <li>
                      <strong class="font-medium text-slate-800">Puestos:</strong> se buscan y agregan de a uno. Si un
                      puesto está asociado a una plantilla activa, esa plantilla gana sobre la del ciclo.
                    </li>
                  </ul>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Qué plantilla usa cada persona</h2>
                  <ol class="mt-2 list-decimal space-y-1 pl-5 text-slate-600">
                    <li>Si su puesto está vinculado a una plantilla activa de la empresa, se usa esa.</li>
                    <li>
                      Si no, se usa la <strong class="font-medium text-slate-800">plantilla por defecto del ciclo</strong>.
                    </li>
                  </ol>
                  <p class="mt-3 text-slate-600">
                    Al activar el ciclo se copian los criterios a ítems de respuesta vacíos. Cambiar la plantilla
                    después no reescribe evaluaciones ya creadas.
                  </p>
                </section>
              </div>
            }
            @case ('ciclos') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Configuración</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Ciclos de evaluación</h1>
                <p class="mt-2 text-sm text-slate-600">
                  Un ciclo es la ventana en la que corre el proceso. Solo puede haber
                  <strong>un ciclo activo por empresa</strong>.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Estados del ciclo</h2>
                  <div class="mt-4 space-y-0">
                    <app-ayuda-paso
                      estado="borrador"
                      contexto="ciclo"
                      titulo="Borrador"
                      texto="Se puede editar nombre, fechas, plantilla y áreas. Todavía no hay evaluaciones."
                    />
                    <app-ayuda-paso
                      estado="activo"
                      contexto="ciclo"
                      titulo="Activo"
                      texto="Al activar desde borrador se crean las evaluaciones. Empleados y supervisores pueden completar. Se puede pausar, reprogramar o cancelar."
                    />
                    <app-ayuda-paso
                      estado="pausado"
                      contexto="ciclo"
                      titulo="Pausado"
                      texto="Nadie edita evaluaciones. Se puede reactivar (si no hay otro ciclo activo) o cancelar. Se notifica a los participantes."
                    />
                    <!-- Django pasa last=True; _paso.html lee ultimo, así que la línea del último paso sigue. -->
                    <app-ayuda-paso
                      estado="cerrado"
                      contexto="ciclo"
                      titulo="Cerrado"
                      texto="Fin del período. No se edita más. Queda para consulta y reportes."
                    />
                  </div>
                  <p class="mt-4 text-slate-600">
                    Desde activo o pausado también se puede <strong class="font-medium text-slate-800">cancelar</strong>
                    (estado terminal). Un ciclo cancelado o cerrado no se reprograma ni se reactiva.
                  </p>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Qué pasa al activar</h2>
                  <ul class="mt-3 list-disc space-y-1 pl-5 text-slate-600">
                    <li>Hace falta al menos un usuario activo, no bloqueado, con puesto.</li>
                    <li>Si el ciclo tiene áreas, solo entran personas de esas áreas.</li>
                    <li>Se crea una evaluación por participante (no se duplica si ya existía).</li>
                    <li>
                      Cada evaluación usa la plantilla del puesto, si hay una activa; si no, la plantilla por defecto
                      del ciclo.
                    </li>
                    <li>Quienes no tengan evaluador quedan listados para que RRHH asigne uno.</li>
                    <li>Se notifica a evaluados y evaluadores.</li>
                  </ul>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Reprogramar</h2>
                  <p class="mt-2 text-slate-600">
                    Se pueden cambiar las fechas mientras el ciclo no esté cerrado ni cancelado. La fecha de cierre no
                    puede ser anterior al inicio. Los participantes reciben aviso del nuevo cierre.
                  </p>
                </section>
              </div>
            }
            @case ('flujo') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Evaluación</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Flujo de una evaluación</h1>
                <p class="mt-2 text-sm text-slate-600">
                  Cada persona tiene una evaluación por ciclo. El estado dice quién tiene que actuar y qué ya quedó
                  bloqueado. El supervisor no ve los puntajes del empleado hasta que cierra su propia evaluación.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Vista rápida</h2>
                  <ol class="mt-3 flex flex-wrap items-center gap-2 text-xs">
                    <li><app-ayuda-badge estado="pendiente_auto" contexto="eval" /></li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li>
                      <app-ayuda-badge estado="auto_borrador" contexto="eval" etiqueta="Borrador empleado" />
                    </li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li>
                      <app-ayuda-badge estado="auto_completa" contexto="eval" etiqueta="Auto completa" />
                    </li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li>
                      <app-ayuda-badge estado="supervisor_borrador" contexto="eval" etiqueta="Borrador supervisor" />
                    </li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li class="rounded-lg border border-dashed border-slate-300 px-2 py-1 text-slate-600">
                      Reunión opcional
                    </li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li><app-ayuda-badge estado="pendiente_conformidad" contexto="eval" /></li>
                    <li class="text-slate-400" aria-hidden="true">→</li>
                    <li><app-ayuda-badge estado="cerrada" contexto="eval" /></li>
                    <li class="text-slate-400">o</li>
                    <li><app-ayuda-badge estado="cerrada_con_obs" contexto="eval" /></li>
                  </ol>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Estados</h2>
                  <div class="mt-4">
                    <app-ayuda-paso
                      estado="pendiente_auto"
                      contexto="eval"
                      titulo="Pendiente de autoevaluación"
                      texto="El empleado todavía no empezó. Puede guardar borrador o enviar."
                    />
                    <app-ayuda-paso
                      estado="auto_borrador"
                      contexto="eval"
                      titulo="Autoevaluación en borrador"
                      texto="Hay puntajes o comentarios guardados, pero no se envió. Sigue pudiendo editar."
                    />
                    <app-ayuda-paso
                      estado="auto_completa"
                      contexto="eval"
                      titulo="Autoevaluación completa"
                      texto="El empleado ya no puede cambiar sus respuestas. El supervisor recibe aviso y puede empezar."
                    />
                    <app-ayuda-paso
                      estado="supervisor_borrador"
                      contexto="eval"
                      titulo="Evaluación de supervisor en borrador"
                      texto="El supervisor guardó sin cerrar. El empleado aún no ve la comparación."
                    />
                    <app-ayuda-paso
                      estado="pendiente_comparacion"
                      contexto="eval"
                      titulo="Pendiente de comparación"
                      texto="El supervisor cerró y pidió reunión de feedback. Hay que registrarla u omitirla (con feedback ya cargado) para habilitar la firma."
                    />
                    <app-ayuda-paso
                      estado="pendiente_conformidad"
                      contexto="eval"
                      titulo="Pendiente de conformidad"
                      texto="El empleado ya ve la comparación y el feedback. Puede firmar o dejar una observación de disconformidad."
                    />
                    <app-ayuda-paso
                      estado="cerrada"
                      contexto="eval"
                      titulo="Cerrada"
                      texto="Firma sin observación. Queda comprobante (hash, fecha e IP) y se puede descargar el PDF."
                    />
                    <app-ayuda-paso
                      estado="cerrada_con_obs"
                      contexto="eval"
                      titulo="Cerrada con observación"
                      texto="El empleado firmó dejando un comentario de disconformidad. RRHH y el supervisor son notificados."
                      [ultimo]="true"
                    />
                  </div>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Quién actúa en cada tramo</h2>
                  <div class="mt-3 overflow-x-auto">
                    <table class="min-w-full text-left">
                      <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                        <tr>
                          <th class="px-3 py-2 font-medium">Tramo</th>
                          <th class="px-3 py-2 font-medium">Empleado</th>
                          <th class="px-3 py-2 font-medium">Supervisor</th>
                          <th class="px-3 py-2 font-medium">RRHH</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        <tr>
                          <td class="px-3 py-2 font-medium text-slate-900">Autoevaluación</td>
                          <td class="px-3 py-2">Completa y envía</td>
                          <td class="px-3 py-2">Espera</td>
                          <td class="px-3 py-2">Supervisa el ciclo</td>
                        </tr>
                        <tr>
                          <td class="px-3 py-2 font-medium text-slate-900">Evaluación de supervisor</td>
                          <td class="px-3 py-2">Espera</td>
                          <td class="px-3 py-2">Puntúa, da feedback y cierra</td>
                          <td class="px-3 py-2">Puede asignar evaluador si faltaba</td>
                        </tr>
                        <tr>
                          <td class="px-3 py-2 font-medium text-slate-900">Reunión (opcional)</td>
                          <td class="px-3 py-2">Espera el registro</td>
                          <td class="px-3 py-2">Registra u omite</td>
                          <td class="px-3 py-2">También puede registrar u omitir</td>
                        </tr>
                        <tr>
                          <td class="px-3 py-2 font-medium text-slate-900">Conformidad</td>
                          <td class="px-3 py-2">Firma u observa</td>
                          <td class="px-3 py-2">Recibe aviso</td>
                          <td class="px-3 py-2">Recibe aviso</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Reglas del flujo</h2>
                  <ul class="mt-3 list-disc space-y-2 pl-5 text-slate-600">
                    <li>Si el ciclo está pausado, cerrado o cancelado, no se editan evaluaciones.</li>
                    <li>
                      Al enviar, los ítems de escala exigen puntaje. La devolución es obligatoria si la plantilla lo
                      marca. Los ítems solo texto no llevan puntaje.
                    </li>
                    <li>El supervisor no puede evaluar antes de que el empleado envíe la autoevaluación.</li>
                    <li>Para cerrar, el supervisor tiene que cargar todos los puntajes y un feedback general.</li>
                    <li>
                      Al cerrar puede habilitar reunión (pasa a pendiente de comparación) o dejar el feedback en el
                      sistema (pasa directo a pendiente de conformidad).
                    </li>
                    <li>La comparación (puntajes lado a lado y brecha) se revela recién cuando el supervisor cerró.</li>
                  </ul>
                </section>
              </div>
            }
            @case ('conformidad') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Evaluación</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Firma y conformidad</h1>
                <p class="mt-2 text-sm text-slate-600">
                  El cierre lo hace el empleado evaluado. Queda un comprobante con fecha, IP y un hash de los puntajes
                  del supervisor.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Camino hasta la firma</h2>
                  <ol class="mt-3 space-y-3">
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">1. El supervisor cierra</p>
                      <p class="mt-1 text-slate-600">
                        Si habilita reunión, el estado pasa a pendiente de comparación. Si no, queda pendiente de
                        conformidad y el empleado ya puede firmar.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">2. Reunión de feedback (opcional)</p>
                      <p class="mt-1 text-slate-600">
                        El supervisor o RRHH registran fecha y notas, o continúan sin reunión si el feedback ya está en
                        el sistema. En ambos casos se habilita la conformidad.
                      </p>
                    </li>
                    <li class="rounded-xl border border-slate-200 bg-white p-4">
                      <p class="font-medium text-slate-900">3. El empleado decide</p>
                      <p class="mt-1 text-slate-600">
                        <strong class="font-medium text-slate-800">Firmar:</strong> la evaluación queda cerrada.
                        <strong class="font-medium text-slate-800">Observar:</strong> queda cerrada con observación y un
                        comentario de disconformidad.
                      </p>
                    </li>
                  </ol>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Comprobante</h2>
                  <p class="mt-2 text-slate-600">
                    La firma genera un hash SHA-256 a partir del id de la evaluación, el usuario, el timestamp y los
                    puntajes del supervisor. También se guarda la IP. El resultado se puede descargar en PDF.
                  </p>
                </section>

                <section class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
                  <p class="font-medium">Importante</p>
                  <p class="mt-1">
                    Solo el evaluado puede firmar, y únicamente en estado pendiente de conformidad. Después del cierre
                    no hay más cambios de puntajes.
                  </p>
                </section>
              </div>
            }
            @case ('notificaciones') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Seguimiento</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Notificaciones</h1>
                <p class="mt-2 text-sm text-slate-600">
                  Cada evento del flujo genera un aviso in-app (campana) y un email. En desarrollo el correo sale por
                  consola.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Eventos del proceso</h2>
                  <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white">
                    <table class="min-w-full text-left">
                      <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                        <tr>
                          <th class="px-4 py-3 font-medium">Evento</th>
                          <th class="px-4 py-3 font-medium">Quién lo recibe</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">
                            Ciclo activado, pausado, cancelado o reprogramado
                          </td>
                          <td class="px-4 py-3">Evaluados y evaluadores del ciclo</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Autoevaluación enviada</td>
                          <td class="px-4 py-3">Supervisor asignado</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Evaluación de supervisor cerrada</td>
                          <td class="px-4 py-3">Empleado evaluado</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Reunión registrada o conformidad habilitada</td>
                          <td class="px-4 py-3">Empleado evaluado</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Evaluador asignado</td>
                          <td class="px-4 py-3">El nuevo evaluador</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Conformidad firmada u observación</td>
                          <td class="px-4 py-3">Supervisor y admins RRHH</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Recordatorio de vencimiento</td>
                          <td class="px-4 py-3">Quienes tienen pendientes en un ciclo activo</td>
                        </tr>
                        <tr>
                          <td class="px-4 py-3 font-medium text-slate-900">Alta, cambio, reset o bloqueo de cuenta</td>
                          <td class="px-4 py-3">El usuario afectado</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Recordatorios</h2>
                  <p class="mt-2 text-slate-600">
                    No hay un scheduler interno. El comando
                    <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">python manage.py enviar_recordatorios</code>
                    avisa a quienes tienen evaluaciones pendientes en un ciclo activo. Con
                    <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">--dry-run</code> se simula sin enviar.
                  </p>
                </section>
              </div>
            }
            @case ('reportes') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Seguimiento</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Reportes ISO 9001</h1>
                <p class="mt-2 text-sm text-slate-600">
                  RRHH (y el superadmin con empresa seleccionada) puede filtrar evaluaciones y exportar PDF o Excel.
                  Cada exportación queda en el log de auditoría.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Filtros</h2>
                  <ul class="mt-3 list-disc space-y-1 pl-5 text-slate-600">
                    <li>Ciclo</li>
                    <li>Área</li>
                    <li>Estado de conformidad (cerrada / cerrada con observación / pendiente)</li>
                    <li>Rango de fechas</li>
                  </ul>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Para qué sirve</h2>
                  <p class="mt-2 text-slate-600">
                    Deja evidencia del proceso de evaluación de desempeño: quién participó, en qué estado quedó cada
                    evaluación y si hubo disconformidad. Complementa el comprobante de firma de cada evaluación
                    individual.
                  </p>
                </section>
              </div>
            }
            @case ('auditoria') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Seguimiento</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Auditoría</h1>
                <p class="mt-2 text-sm text-slate-600">
                  Queda un registro de las acciones relevantes, acotado a la empresa del contexto. Las claves sensibles
                  (contraseñas, tokens, etc.) no se guardan en el payload.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Qué se registra</h2>
                  <ul class="mt-3 list-disc space-y-1 pl-5 text-slate-600">
                    <li>Login, logout y login fallido</li>
                    <li>Altas, ediciones, desactivaciones y suspensiones</li>
                    <li>Activar, pausar, cancelar y reprogramar un ciclo</li>
                    <li>Guardar o enviar autoevaluación y evaluación de supervisor</li>
                    <li>Registrar u omitir reunión de feedback</li>
                    <li>Firmar conformidad u observar</li>
                    <li>Asignar evaluador</li>
                    <li>Exportar reportes ISO</li>
                  </ul>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Qué incluye cada registro</h2>
                  <p class="mt-2 text-slate-600">
                    Usuario, empresa, acción, modelo e id del objeto, payload (datos no sensibles), IP, user agent y
                    fecha. Solo RRHH y superadmin (con empresa) pueden consultarlo.
                  </p>
                </section>
              </div>
            }
            @case ('empresas') {
              <header class="mb-6">
                <p class="text-xs font-medium uppercase tracking-wide text-sky-700">Plataforma</p>
                <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Empresas y plataforma</h1>
                <p class="mt-2 text-sm text-slate-600">
                  TeamPulse es multi-tenant. Cada empresa aísla usuarios, organización, evaluaciones, notificaciones,
                  reportes y auditoría.
                </p>
              </header>

              <div class="space-y-8 text-sm text-slate-700">
                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Estados de la empresa</h2>
                  <div class="mt-4">
                    <app-ayuda-paso
                      estado="activa"
                      badge="empresa"
                      titulo="Activa"
                      texto="Los usuarios de la empresa pueden iniciar sesión y operar."
                    />
                    <app-ayuda-paso
                      estado="suspendida"
                      badge="empresa"
                      titulo="Suspendida"
                      texto="Nadie de esa empresa autentica. El superadmin puede reactivarla."
                    />
                    <app-ayuda-paso
                      estado="inactiva"
                      badge="empresa"
                      titulo="Inactiva"
                      texto="Fuera de operación. Tampoco permite login."
                      [ultimo]="true"
                    />
                  </div>
                </section>

                <section class="rounded-xl border border-slate-200 bg-white p-4">
                  <h2 class="font-semibold text-slate-900">Selector de contexto</h2>
                  <p class="mt-2 text-slate-600">
                    El superadmin elige la empresa desde el encabezado. Sin empresa seleccionada solo ve el panel de
                    plataforma y el ABM de empresas. Con empresa, opera como RRHH de ese tenant (usuarios, ciclos,
                    reportes, auditoría).
                  </p>
                </section>

                <section>
                  <h2 class="text-lg font-semibold text-slate-900">Datos de la empresa</h2>
                  <p class="mt-2 text-slate-600">
                    Nombre, razón social, CUIT (único y validado), email de contacto, teléfono, dirección y parámetros
                    JSON opcionales.
                  </p>
                </section>
              </div>
            }
      }
    } @else if (estado() === 'denegado') {
      <p class="text-sm text-slate-700">No tenés permiso para acceder a esta sección.</p>
    } @else {
      <p class="text-sm text-slate-700">No encontramos esa guía.</p>
    }
  `,
})
export class AyudaPaginaPage {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly title = inject(Title);
  private readonly paramMap = toSignal(this.route.paramMap, { initialValue: this.route.snapshot.paramMap });

  readonly slug = computed(() => this.paramMap().get('slug') ?? '');
  readonly rol = computed(() => this.auth.sesion()?.usuario.rol);
  readonly visibles = computed(() => paginasVisibles(this.rol()));
  readonly pagina = computed(() => paginaPorSlug(this.slug()));
  readonly estado = computed<'ok' | 'denegado' | 'no-existe'>(() => {
    const pagina = this.pagina();
    if (!pagina) return 'no-existe';
    return this.visibles().some((item) => item.slug === pagina.slug) ? 'ok' : 'denegado';
  });
  readonly muestraConfig = computed(() => {
    const slugs = new Set(this.visibles().map((item) => item.slug));
    return slugs.has('organizacion') && slugs.has('ciclos');
  });

  constructor() {
    effect(() => {
      const pagina = this.pagina();
      this.title.setTitle(this.estado() === 'ok' && pagina ? `${pagina.titulo} · TeamPulse` : 'Ayuda · TeamPulse');
    });
  }
}
