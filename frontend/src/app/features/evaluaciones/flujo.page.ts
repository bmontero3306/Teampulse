import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { combineLatest } from 'rxjs';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import { BadgeEstadoFlujoComponent } from './badge-estado-flujo.component';
import { FormularioItemsComponent } from './formulario-items.component';
import {
  CicloFlujo,
  EvaluacionDetalle,
  EvaluacionLista,
  RespuestaFlujo,
  agruparItems,
  brechaDisplay,
  cargarCiclosVisibles,
  cargarDescripciones,
  esTexto,
  fechaHoraLarga,
  fechaLarga,
  nombrePersona,
} from './flujo-modelos';

@Component({
  selector: 'app-mias',
  imports: [RouterLink, BadgeEstadoFlujoComponent],
  template: `
    <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Mis evaluaciones</h1>
    <p class="mt-1 text-sm text-slate-600">Autoevaluación, comparación 180° y firma de conformidad.</p>

    @if (listo()) {
      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 font-medium">Ciclo</th>
              <th class="px-4 py-3 font-medium">Estado</th>
              <th class="px-4 py-3 font-medium">Vencimiento</th>
              <th class="px-4 py-3 font-medium">Evaluador</th>
              <th class="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (ev of lista(); track ev.id) {
              <tr>
                <td class="px-4 py-3 font-medium text-slate-900">{{ ev.ciclo_nombre }}</td>
                <td class="px-4 py-3">
                  <app-badge-estado-flujo [estado]="ev.estado" [etiqueta]="ev.estado_display" />
                </td>
                <td class="px-4 py-3 text-slate-600 whitespace-nowrap">{{ vencimiento(ev) }}</td>
                <td class="px-4 py-3 text-slate-600">{{ nombre(ev.evaluador) }}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <a [routerLink]="accion(ev).ruta" class="font-medium text-sky-700 hover:text-sky-900">{{ accion(ev).texto }}</a>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="px-4 py-8 text-center text-slate-500">No tenés evaluaciones asignadas.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class MiasPage {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly alertas = inject(AlertService);
  private readonly title = inject(Title);
  lista = signal<EvaluacionLista[]>([]);
  ciclos = signal<Record<number, CicloFlujo>>({});
  listo = signal(false);
  readonly nombre = nombrePersona;

  constructor() {
    this.title.setTitle('Mis evaluaciones · TeamPulse');
    this.http.get<EvaluacionLista[]>(`${API}/evaluaciones/mias/`).subscribe({
      next: (lista) => {
        this.lista.set(lista);
        this.listo.set(true);
        cargarCiclosVisibles(
          this.http,
          lista.map((ev) => ev.ciclo),
          this.auth.sesion()?.usuario.rol,
        ).subscribe((mapa) => this.ciclos.set(mapa));
      },
      error: (err) => {
        this.listo.set(true);
        this.alertas.error(mensajeError(err));
      },
    });
  }

  vencimiento(ev: EvaluacionLista): string {
    return fechaLarga(this.ciclos()[ev.ciclo]?.fecha_cierre);
  }

  accion(ev: EvaluacionLista): { ruta: string[]; texto: string } {
    if (ev.estado === 'pendiente_auto' || ev.estado === 'auto_borrador') {
      return { ruta: ['/evaluaciones', String(ev.id), 'autoevaluacion'], texto: 'Completar' };
    }
    if (ev.estado === 'pendiente_comparacion') {
      return { ruta: ['/evaluaciones', String(ev.id), 'resultado'], texto: 'Ver comparación' };
    }
    if (ev.estado === 'pendiente_conformidad') {
      return { ruta: ['/evaluaciones', String(ev.id), 'resultado'], texto: 'Firmar' };
    }
    return { ruta: ['/evaluaciones', String(ev.id), 'resultado'], texto: 'Ver resultado' };
  }
}

@Component({
  selector: 'app-equipo',
  imports: [RouterLink, BadgeEstadoFlujoComponent],
  template: `
    <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Equipo a cargo</h1>
    <p class="mt-1 text-sm text-slate-600">Evaluaciones de tus colaboradores.</p>

    @if (listo()) {
      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 font-medium">Colaborador</th>
              <th class="px-4 py-3 font-medium">Ciclo</th>
              <th class="px-4 py-3 font-medium">Estado</th>
              <th class="px-4 py-3 font-medium">Vencimiento</th>
              <th class="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (ev of lista(); track ev.id) {
              <tr>
                <td class="px-4 py-3 font-medium text-slate-900">{{ nombre(ev.evaluado) }}</td>
                <td class="px-4 py-3 text-slate-600">{{ ev.ciclo_nombre }}</td>
                <td class="px-4 py-3">
                  <app-badge-estado-flujo [estado]="ev.estado" [etiqueta]="ev.estado_display" />
                </td>
                <td class="px-4 py-3 text-slate-600 whitespace-nowrap">{{ vencimiento(ev) }}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  @if (esperaAuto(ev)) {
                    <span class="text-slate-400">Espera autoevaluación</span>
                  } @else {
                    <a [routerLink]="accion(ev).ruta" class="font-medium text-sky-700 hover:text-sky-900">{{ accion(ev).texto }}</a>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="px-4 py-8 text-center text-slate-500">No hay colaboradores asignados.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class EquipoPage {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly alertas = inject(AlertService);
  private readonly title = inject(Title);
  lista = signal<EvaluacionLista[]>([]);
  ciclos = signal<Record<number, CicloFlujo>>({});
  listo = signal(false);
  readonly nombre = nombrePersona;

  constructor() {
    this.title.setTitle('Mi equipo · TeamPulse');
    this.http.get<EvaluacionLista[]>(`${API}/evaluaciones/equipo/`).subscribe({
      next: (lista) => {
        this.lista.set(lista);
        this.listo.set(true);
        cargarCiclosVisibles(
          this.http,
          lista.map((ev) => ev.ciclo),
          this.auth.sesion()?.usuario.rol,
        ).subscribe((mapa) => this.ciclos.set(mapa));
      },
      error: (err) => {
        this.listo.set(true);
        this.alertas.error(mensajeError(err));
      },
    });
  }

  vencimiento(ev: EvaluacionLista): string {
    return fechaLarga(this.ciclos()[ev.ciclo]?.fecha_cierre);
  }

  esperaAuto(ev: EvaluacionLista): boolean {
    return ev.estado === 'pendiente_auto' || ev.estado === 'auto_borrador';
  }

  accion(ev: EvaluacionLista): { ruta: string[]; texto: string } {
    if (ev.estado === 'auto_completa' || ev.estado === 'supervisor_borrador') {
      return { ruta: ['/evaluaciones', String(ev.id), 'supervisar'], texto: 'Evaluar' };
    }
    return { ruta: ['/evaluaciones', String(ev.id), 'resultado'], texto: 'Ver comparación' };
  }
}

@Component({
  selector: 'app-flujo',
  imports: [RouterLink, FormsModule, BadgeEstadoFlujoComponent, FormularioItemsComponent],
  template: `
    @if (ev(); as actual) {
      @if (modo() === 'auto') {
        <a routerLink="/evaluaciones/mias" class="text-sm font-medium text-sky-700 hover:text-sky-900">← Mis evaluaciones</a>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Autoevaluación</h1>
        <p class="mt-1 text-sm text-slate-600">
          Ciclo «{{ actual.ciclo_nombre }}» · vencimiento {{ vencimiento() }}.
          @if (criteriosGenerales()) {
            {{ criteriosGenerales() }}
          }
        </p>
        <div class="mt-2">
          <app-badge-estado-flujo [estado]="actual.estado" [etiqueta]="actual.estado_display" />
        </div>

        @if (soloLectura()) {
          <p class="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            La autoevaluación ya fue enviada y no se puede modificar.
          </p>
        }

        <form class="mt-6 space-y-4" (submit)="enviarAuto($event)">
          <app-formulario-items
            [items]="respuestas()"
            rol="empleado"
            [lectura]="soloLectura()"
            [descripciones]="descripciones()"
          />
          @if (!soloLectura()) {
            <div class="flex flex-col gap-3 sm:flex-row">
              <button type="submit" name="accion" value="borrador" class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                Guardar borrador
              </button>
              <button type="submit" name="accion" value="enviar" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
                Enviar definitivo
              </button>
            </div>
          }
        </form>
      } @else if (modo() === 'supervisar') {
        <a routerLink="/evaluaciones/equipo" class="text-sm font-medium text-sky-700 hover:text-sky-900">← Equipo</a>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          Evaluar a {{ nombre(actual.evaluado) }}
        </h1>
        <p class="mt-1 text-sm text-slate-600">Ciclo «{{ actual.ciclo_nombre }}» · evaluación independiente, sin ver la autoevaluación.</p>
        <div class="mt-2">
          <app-badge-estado-flujo [estado]="actual.estado" [etiqueta]="actual.estado_display" />
        </div>

        @if (!puedeEditar()) {
          <p class="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            Esta evaluación ya no admite cambios del supervisor.
          </p>
        }

        <form class="mt-6 space-y-4" (submit)="enviarSupervisor($event)">
          <app-formulario-items
            [items]="respuestas()"
            rol="supervisor"
            [lectura]="!puedeEditar()"
            [descripciones]="descripciones()"
          />

          <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="feedback-supervisor">
              Feedback del supervisor (obligatorio al cerrar)
            </label>
            <textarea
              id="feedback-supervisor"
              name="feedback_supervisor"
              rows="4"
              class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-24"
              [(ngModel)]="feedback"
              [disabled]="!puedeEditar()"
            ></textarea>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <label class="flex items-start gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                name="habilitar_reunion"
                class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                [(ngModel)]="habilitarReunion"
                [disabled]="!puedeEditar()"
              />
              <span>
                <span class="font-medium">Habilitar reunión de feedback</span>
                <span class="mt-1 block text-slate-500">Opcional. Si no la marcás, el empleado ve la comparación y firma con el feedback y las observaciones del sistema.</span>
              </span>
            </label>
          </section>

          @if (puedeEditar()) {
            <div class="flex flex-col gap-3 sm:flex-row">
              <button type="submit" name="accion" value="borrador" class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                Guardar borrador
              </button>
              <button type="submit" name="accion" value="cerrar" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
                Cerrar evaluación
              </button>
            </div>
          }
        </form>
      } @else {
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <a [routerLink]="volver().ruta" class="text-sm font-medium text-sky-700 hover:text-sky-900">{{ volver().etiqueta }}</a>
            <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
              @if (actual.comparacion_revelada) { Comparación 180° } @else { Resultado de la evaluación }
            </h1>
            <p class="mt-1 text-sm text-slate-600">
              Ciclo «{{ actual.ciclo_nombre }}»@if (!esEvaluado()) { · {{ nombre(actual.evaluado) }} }
            </p>
            <div class="mt-2">
              <app-badge-estado-flujo [estado]="actual.estado" [etiqueta]="actual.estado_display" />
            </div>
          </div>
          <a
            [href]="pdfHref()"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
            (click)="imprimir($event)"
          >
            Imprimir PDF
          </a>
        </div>

        @if (!actual.comparacion_revelada) {
          <p class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            El resultado del supervisor todavía no está cerrado. La comparación se revela cuando el jefe envía su evaluación.
          </p>
        } @else if (actual.estado === 'pendiente_comparacion') {
          <p class="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
            @if (esEvaluado()) {
              Ya podés comparar ambas evaluaciones. El supervisor habilitó una reunión de feedback; la firma se habilita cuando se registre o se continúe con el feedback del sistema.
            } @else {
              Compará ambas evaluaciones. Podés registrar la reunión de feedback o continuar sin reunión para que el empleado firme con el feedback del sistema.
            }
          </p>
        }

        <div class="mt-6 space-y-4">
          @for (grupo of grupos(); track $index) {
            <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              @if (grupo.nombre) {
                <h2 class="border-b border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-800">
                  {{ grupo.nombre }}
                </h2>
              }
              <table class="min-w-[720px] w-full text-left text-sm">
                <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                  <tr>
                    <th class="px-3 py-2 font-medium">Criterio</th>
                    <th class="px-3 py-2 font-medium">@if (esEvaluado()) { Tu puntaje } @else { Empleado }</th>
                    <th class="px-3 py-2 font-medium">@if (esEvaluado()) { Tu devolución } @else { Devolución empleado }</th>
                    <th class="px-3 py-2 font-medium">Puntaje supervisor</th>
                    <th class="px-3 py-2 font-medium">Devolución supervisor</th>
                    @if (actual.comparacion_revelada) {
                      <th class="px-3 py-2 font-medium">Brecha</th>
                    }
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 align-top">
                  @for (item of grupo.items; track item.id) {
                    <tr>
                      <td class="px-3 py-2">
                        <p class="font-medium text-slate-900">{{ item.competencia }}</p>
                        @if (descripcion(item)) {
                          <p class="mt-0.5 text-xs text-slate-500">{{ descripcion(item) }}</p>
                        }
                      </td>
                      <td class="px-3 py-2">
                        @if (esTexto(item)) { — } @else { {{ item.puntaje_empleado ?? '—' }} }
                      </td>
                      <td class="px-3 py-2 text-slate-600 whitespace-pre-line">{{ item.comentario_empleado || '—' }}</td>
                      <td class="px-3 py-2">
                        @if (actual.comparacion_revelada) {
                          @if (esTexto(item)) { — } @else { {{ item.puntaje_supervisor ?? '—' }} }
                        } @else { — }
                      </td>
                      <td class="px-3 py-2 text-slate-600 whitespace-pre-line">
                        @if (actual.comparacion_revelada) { {{ item.comentario_supervisor || '—' }} } @else { — }
                      </td>
                      @if (actual.comparacion_revelada) {
                        <td class="px-3 py-2 font-medium text-slate-800">{{ textoBrecha(item) }}</td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @empty {
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
              Sin ítems.
            </div>
          }
        </div>

        @if (actual.comparacion_revelada && actual.feedback_supervisor) {
          <section class="mt-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-slate-900">Feedback del supervisor</h2>
            @if (!actual.reunion_notas && actual.estado !== 'pendiente_comparacion') {
              <p class="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">Por el sistema, sin reunión</p>
            }
            <p class="mt-2 whitespace-pre-line text-sm text-slate-700">{{ actual.feedback_supervisor }}</p>
          </section>
        }

        @if (actual.reunion_notas) {
          <section class="mt-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-slate-900">Reunión de feedback</h2>
            <dl class="mt-3 grid gap-2 text-sm text-slate-700">
              @if (actual.reunion_fecha) {
                <div>
                  <dt class="font-medium text-slate-900">Fecha</dt>
                  <dd>{{ fechaHora(actual.reunion_fecha) }}</dd>
                </div>
              }
              <div>
                <dt class="font-medium text-slate-900">Notas</dt>
                <dd class="mt-1 whitespace-pre-line">{{ actual.reunion_notas }}</dd>
              </div>
            </dl>
          </section>
        }

        @if (puedeRegistrarReunion()) {
          <section class="mt-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-slate-900">Reunión de feedback (opcional)</h2>
            <p class="mt-1 text-sm text-slate-600">Si la registrás, el empleado firma después de la reunión. Si no, el feedback y las observaciones quedan en el sistema.</p>
            <form class="mt-4 space-y-4" (submit)="registrarReunion($event)">
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="reunion-fecha">Fecha de la reunión</label>
                <input
                  id="reunion-fecha"
                  name="reunion_fecha"
                  type="datetime-local"
                  class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  [(ngModel)]="reunionFecha"
                />
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="reunion-notas">Notas</label>
                <textarea
                  id="reunion-notas"
                  name="reunion_notas"
                  rows="4"
                  class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-24"
                  [(ngModel)]="reunionNotas"
                ></textarea>
              </div>
              <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
                Registrar reunión
              </button>
            </form>
            <form class="mt-4 border-t border-slate-200 pt-4" (submit)="omitirReunion($event)">
              <p class="text-sm text-slate-600">Sin reunión, el empleado firma con el feedback y las observaciones ya cargados.</p>
              <button type="submit" name="accion" value="omitir_reunion" class="mt-3 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                Continuar sin reunión
              </button>
            </form>
          </section>
        }

        @if (actual.firma_hash) {
          <section class="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-emerald-900">Comprobante de firma</h2>
            <dl class="mt-3 grid gap-2 text-sm text-emerald-950">
              <div>
                <dt class="font-medium">Fecha y hora</dt>
                <dd>{{ fechaHora(actual.firmada_en) }}</dd>
              </div>
              <div>
                <dt class="font-medium">Código de firma</dt>
                <dd class="break-all font-mono text-xs">{{ actual.firma_hash }}</dd>
              </div>
              @if (actual.comentario_empleado_cierre) {
                <div>
                  <dt class="font-medium">Observación de disconformidad</dt>
                  <dd class="whitespace-pre-line">{{ actual.comentario_empleado_cierre }}</dd>
                </div>
              }
            </dl>
          </section>
        }

        @if (puedeFirmar()) {
          <section class="mt-6 space-y-4">
            <form class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6" (submit)="firmarConformidad($event)">
              <h2 class="text-lg font-semibold text-slate-900">Firmar conformidad</h2>
              <p class="mt-1 text-sm text-slate-600">Confirmás que leíste el resultado de tu evaluación.</p>
              <button type="submit" name="accion" value="conformidad" class="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
                Firmar conformidad
              </button>
            </form>

            <form class="rounded-xl border border-red-200 bg-white p-4 sm:p-6" (submit)="firmarObservacion($event)">
              <h2 class="text-lg font-semibold text-slate-900">Observación de disconformidad</h2>
              <p class="mt-1 text-sm text-slate-600">Registrá tu observación y cerrá el proceso con constancia.</p>
              <div class="mt-3">
                <textarea
                  name="observacion"
                  rows="4"
                  class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-24"
                  [(ngModel)]="observacion"
                ></textarea>
              </div>
              <button type="submit" name="accion" value="observacion" class="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">
                Observar y cerrar
              </button>
            </form>
          </section>
        }
      }
    }
  `,
})
export class FlujoPage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  private readonly title = inject(Title);

  ev = signal<EvaluacionDetalle | null>(null);
  modo = signal<'auto' | 'supervisar' | 'resultado'>('auto');
  descripciones = signal<Record<string, string>>({});
  cicloCtx = signal<CicloFlujo | null>(null);
  grupos = computed(() => agruparItems(this.ev()?.respuestas ?? []));
  respuestas = computed(() => this.ev()?.respuestas ?? []);

  feedback = '';
  habilitarReunion = false;
  reunionFecha = '';
  reunionNotas = '';
  observacion = '';
  private solicitud = 0;

  readonly nombre = nombrePersona;
  readonly fechaHora = fechaHoraLarga;
  readonly esTexto = esTexto;

  constructor() {
    combineLatest([this.route.data, this.route.paramMap])
      .pipe(takeUntilDestroyed())
      .subscribe(([data, params]) => {
        const modo = (data['modo'] as 'auto' | 'supervisar' | 'resultado') ?? 'auto';
        this.modo.set(modo);
        this.ev.set(null);
        this.cicloCtx.set(null);
        this.title.setTitle(`${this.tituloDocumento(modo)} · TeamPulse`);
        this.cargar(params.get('id'), modo);
      });
  }

  soloLectura(): boolean {
    const estado = this.ev()?.estado;
    return estado !== 'pendiente_auto' && estado !== 'auto_borrador';
  }

  puedeEditar(): boolean {
    const estado = this.ev()?.estado;
    return estado === 'auto_completa' || estado === 'supervisor_borrador';
  }

  esEvaluado(): boolean {
    return this.ev()?.evaluado?.id === this.auth.sesion()?.usuario.id;
  }

  puedeFirmar(): boolean {
    const actual = this.ev();
    const usuario = this.auth.sesion()?.usuario;
    return !!actual && !!usuario && actual.evaluado?.id === usuario.id && actual.estado === 'pendiente_conformidad';
  }

  puedeRegistrarReunion(): boolean {
    const actual = this.ev();
    const usuario = this.auth.sesion()?.usuario;
    if (!actual || !usuario || actual.estado !== 'pendiente_comparacion') {
      return false;
    }
    return actual.evaluador?.id === usuario.id || usuario.rol === 'admin_rrhh' || usuario.rol === 'superadmin';
  }

  vencimiento(): string {
    return fechaLarga(this.cicloCtx()?.fecha_cierre);
  }

  criteriosGenerales(): string {
    return (this.cicloCtx()?.criterios_generales || '').trim();
  }

  descripcion(item: RespuestaFlujo): string {
    return (this.descripciones()[item.competencia] || '').trim();
  }

  textoBrecha(item: RespuestaFlujo): string {
    return brechaDisplay(item.brecha, esTexto(item));
  }

  volver(): { ruta: string[]; etiqueta: string } {
    const actual = this.ev();
    const yo = this.auth.sesion()?.usuario.id;
    if (!actual || actual.evaluado?.id === yo) {
      return { ruta: ['/evaluaciones/mias'], etiqueta: '← Mis evaluaciones' };
    }
    if (actual.evaluador?.id === yo) {
      return { ruta: ['/evaluaciones/equipo'], etiqueta: '← Equipo' };
    }
    return { ruta: ['/evaluaciones/ciclos', String(actual.ciclo)], etiqueta: '← Ciclo' };
  }

  pdfHref(): string {
    const id = this.ev()?.id;
    return id ? `${API}/evaluaciones/${id}/resultado.pdf` : '#';
  }

  enviarAuto(event: Event): void {
    event.preventDefault();
    const accion = this.accionSubmit(event);
    if (accion === 'enviar' && !window.confirm('¿Enviar la autoevaluación definitiva? No vas a poder editarla después.')) {
      return;
    }
    this.guardarAuto(accion === 'enviar');
  }

  enviarSupervisor(event: Event): void {
    event.preventDefault();
    const accion = this.accionSubmit(event);
    if (
      accion === 'cerrar' &&
      !window.confirm(
        '¿Cerrar la evaluación de supervisor? Se revelarán ambas evaluaciones. Si no habilitás reunión, el empleado firma con el feedback del sistema.',
      )
    ) {
      return;
    }
    this.guardarSupervisor(accion === 'cerrar');
  }

  registrarReunion(event: Event): void {
    event.preventDefault();
    const actual = this.ev();
    if (!actual) {
      return;
    }
    const notas = this.reunionNotas.trim();
    if (!this.reunionFecha || !notas) {
      this.alertas.error('Revisá la fecha y las notas de la reunión.');
      return;
    }
    const fecha = this.reunionFecha.length === 16 ? `${this.reunionFecha}:00` : this.reunionFecha;
    this.http
      .post<EvaluacionDetalle>(`${API}/evaluaciones/${actual.id}/reunion/`, {
        reunion_fecha: fecha,
        reunion_notas: notas,
      })
      .subscribe({
        next: (ev) => {
          this.aplicar(ev);
          this.alertas.success('Reunión de feedback registrada.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  omitirReunion(event: Event): void {
    event.preventDefault();
    if (!window.confirm('¿Continuar sin reunión? El empleado firmará con el feedback del sistema.')) {
      return;
    }
    const actual = this.ev();
    if (!actual) {
      return;
    }
    this.http.post<EvaluacionDetalle>(`${API}/evaluaciones/${actual.id}/omitir-reunion/`, {}).subscribe({
      next: (ev) => {
        this.aplicar(ev);
        this.alertas.success('Se continuó sin reunión. El empleado puede firmar con el feedback del sistema.');
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  firmarConformidad(event: Event): void {
    event.preventDefault();
    if (!window.confirm('¿Firmar la conformidad de esta evaluación?')) {
      return;
    }
    this.enviarFirma(null, 'Conformidad firmada.');
  }

  firmarObservacion(event: Event): void {
    event.preventDefault();
    const texto = this.observacion.trim();
    if (!texto) {
      this.alertas.error('La observación de disconformidad es obligatoria.');
      return;
    }
    if (!window.confirm('¿Registrar la observación de disconformidad y cerrar?')) {
      return;
    }
    this.enviarFirma(texto, 'Se registró la observación de disconformidad.');
  }

  imprimir(event: Event): void {
    event.preventDefault();
    const id = this.ev()?.id;
    if (!id) {
      return;
    }
    this.http.get(`${API}/evaluaciones/${id}/resultado.pdf`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noopener');
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      },
      error: () => this.alertas.error('No se pudo imprimir el PDF.'),
    });
  }

  private cargar(id: string | null, modo: 'auto' | 'supervisar' | 'resultado'): void {
    if (!id) {
      return;
    }
    const solicitud = ++this.solicitud;
    const path = modo === 'auto' ? 'autoevaluacion' : modo === 'supervisar' ? 'supervisar' : 'resultado';
    this.http.get<EvaluacionDetalle>(`${API}/evaluaciones/${id}/${path}/`).subscribe({
      next: (ev) => {
        if (solicitud !== this.solicitud) {
          return;
        }
        this.aplicar(ev);
        if (modo === 'auto') {
          cargarCiclosVisibles(this.http, [ev.ciclo], this.auth.sesion()?.usuario.rol).subscribe((mapa) => {
            if (solicitud !== this.solicitud) {
              return;
            }
            this.cicloCtx.set(mapa[ev.ciclo] ?? null);
          });
        }
        cargarDescripciones(this.http).subscribe((mapa) => this.descripciones.set(mapa));
      },
      error: (err) => {
        if (solicitud !== this.solicitud) {
          return;
        }
        this.alertas.error(mensajeError(err));
      },
    });
  }

  private aplicar(ev: EvaluacionDetalle): void {
    this.ev.set({
      ...ev,
      respuestas: [...(ev.respuestas ?? [])],
    });
    this.feedback = ev.feedback_supervisor ?? '';
    this.habilitarReunion = false;
    this.reunionFecha = '';
    this.reunionNotas = '';
    this.observacion = '';
  }

  private guardarAuto(enviar: boolean): void {
    const actual = this.ev();
    if (!actual) {
      return;
    }
    this.http
      .put<EvaluacionDetalle>(`${API}/evaluaciones/${actual.id}/autoevaluacion/`, {
        enviar,
        respuestas: this.respuestas().map((item) => ({
          id: item.id,
          puntaje_empleado: esTexto(item) ? null : item.puntaje_empleado,
          comentario_empleado: item.comentario_empleado ?? '',
        })),
      })
      .subscribe({
        next: (ev) => {
          if (enviar) {
            this.alertas.success('Autoevaluación enviada.');
            this.router.navigate(['/evaluaciones/mias']);
            return;
          }
          this.aplicar(ev);
          this.alertas.success('Autoevaluación guardada como borrador.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  private guardarSupervisor(cerrar: boolean): void {
    const actual = this.ev();
    if (!actual) {
      return;
    }
    this.http
      .put<EvaluacionDetalle>(`${API}/evaluaciones/${actual.id}/supervisar/`, {
        cerrar,
        habilitar_reunion: this.habilitarReunion,
        feedback_supervisor: this.feedback,
        respuestas: this.respuestas().map((item) => ({
          id: item.id,
          puntaje_supervisor: esTexto(item) ? null : item.puntaje_supervisor,
          comentario_supervisor: item.comentario_supervisor ?? '',
        })),
      })
      .subscribe({
        next: (ev) => {
          if (cerrar) {
            this.alertas.success('Evaluación de supervisor cerrada. Ya podés comparar ambas evaluaciones.');
            this.router.navigate(['/evaluaciones', actual.id, 'resultado']);
            return;
          }
          this.aplicar(ev);
          this.alertas.success('Evaluación de supervisor guardada.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  private enviarFirma(observacion: string | null, mensaje: string): void {
    const actual = this.ev();
    if (!actual) {
      return;
    }
    const cuerpo = observacion ? { observacion } : {};
    this.http.post<EvaluacionDetalle>(`${API}/evaluaciones/${actual.id}/firmar/`, cuerpo).subscribe({
      next: (ev) => {
        this.aplicar(ev);
        this.alertas.success(mensaje);
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  private accionSubmit(event: Event): string {
    const submitter = (event as SubmitEvent).submitter;
    return submitter?.getAttribute('value') ?? '';
  }

  private tituloDocumento(modo: 'auto' | 'supervisar' | 'resultado'): string {
    if (modo === 'auto') {
      return 'Autoevaluación';
    }
    if (modo === 'supervisar') {
      return 'Supervisar evaluación';
    }
    return 'Resultado';
  }
}
