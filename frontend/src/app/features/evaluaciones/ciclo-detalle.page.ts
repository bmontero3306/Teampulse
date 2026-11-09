import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import { BadgeEstadoComponent } from './badge-estado.component';
import {
  AreaOpcion,
  CandidatoEvaluador,
  CicloApi,
  INPUT_CSS,
  ParticipanteApi,
  PlantillaApi,
  TEXTAREA_CSS,
  erroresVacios,
  esGestion,
  fechaCorta,
  listarTodo,
  ordenarParticipantes,
  parsearErrores,
  progresoCiclo,
  type ErroresApi,
} from './evaluaciones-ui';

type AccionCiclo = 'activar' | 'pausar' | 'cancelar';

interface ConfirmacionCiclo {
  accion: AccionCiclo;
  titulo: string;
  mensaje: string;
  confirmacion: string;
  peligro: boolean;
}

interface ParticipanteVista extends ParticipanteApi {
  candidatos: CandidatoEvaluador[];
}

const TEXTOS: Record<AccionCiclo, Omit<ConfirmacionCiclo, 'accion' | 'mensaje'> & { mensaje: (nombre: string) => string }> = {
  activar: {
    titulo: 'Activar ciclo',
    mensaje: (nombre) =>
      `Vas a activar el ciclo «${nombre}». Se generarán las evaluaciones de los empleados con puesto.`,
    confirmacion: 'Activar ciclo',
    peligro: false,
  },
  pausar: {
    titulo: 'Pausar ciclo',
    mensaje: (nombre) => `Vas a pausar el ciclo «${nombre}». El historial se conserva.`,
    confirmacion: 'Pausar ciclo',
    peligro: false,
  },
  cancelar: {
    titulo: 'Cancelar ciclo',
    mensaje: (nombre) =>
      `Vas a cancelar el ciclo «${nombre}». No se borra el historial, pero se bloquean nuevas ediciones.`,
    confirmacion: 'Cancelar ciclo',
    peligro: true,
  },
};

@Component({
  selector: 'app-ciclo-detalle',
  imports: [ReactiveFormsModule, RouterLink, BadgeEstadoComponent],
  template: `
    @if (vista() === 'reprogramar' && ciclo(); as actual) {
      <section class="mx-auto max-w-lg">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Reprogramar ciclo</h1>
        <p class="mt-2 text-sm text-slate-600">Cambiás las fechas de «{{ actual.nombre }}». El historial se conserva.</p>
        <form class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-4 sm:p-6" [formGroup]="fechas" (ngSubmit)="guardarFechas()">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="reprog-inicio">Fecha de inicio</label>
            <input id="reprog-inicio" type="date" formControlName="fecha_inicio" [class]="inputCss" />
            @if (mensajesFecha('fecha_inicio'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="reprog-cierre">Fecha de cierre</label>
            <input id="reprog-cierre" type="date" formControlName="fecha_cierre" [class]="inputCss" />
            @if (mensajesFecha('fecha_cierre'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="flex flex-wrap gap-3">
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
              Guardar fechas
            </button>
            <a
              [routerLink]="['/evaluaciones/ciclos', actual.id]"
              class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Cancelar
            </a>
          </div>
        </form>
      </section>
    } @else if (vista() === 'confirmar' && confirmacion(); as pedido) {
      <section class="mx-auto max-w-lg">
        <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ pedido.titulo }}</h1>
          <p class="mt-3 text-sm text-slate-600">{{ pedido.mensaje }}</p>
          <form class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end" (ngSubmit)="ejecutar()">
            <a
              [routerLink]="['/evaluaciones/ciclos', ciclo()?.id]"
              class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Volver
            </a>
            <button
              type="submit"
              [class]="
                'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-white ' +
                (pedido.peligro ? 'bg-red-600 hover:bg-red-700' : 'bg-sky-600 hover:bg-sky-700')
              "
            >
              {{ pedido.confirmacion }}
            </button>
          </form>
        </div>
      </section>
    } @else if (ciclo(); as actual) {
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <a routerLink="/evaluaciones/ciclos" class="text-sm font-medium text-sky-700 hover:text-sky-900">← Ciclos</a>
          <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{{ actual.nombre }}</h1>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <app-badge-estado [estado]="actual.estado" contexto="ciclo" />
            <span class="text-sm text-slate-600">{{ fecha(actual.fecha_inicio) }} → {{ fecha(actual.fecha_cierre) }}</span>
          </div>
        </div>
        @if (puedeGestionar()) {
          <div class="flex flex-wrap gap-2">
            @if (actual.estado === 'borrador' || actual.estado === 'pausado') {
              <a
                [routerLink]="['/evaluaciones/ciclos', actual.id, 'activar']"
                class="rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700"
              >
                Activar
              </a>
            }
            @if (actual.estado === 'activo') {
              <a
                [routerLink]="['/evaluaciones/ciclos', actual.id, 'pausar']"
                class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Pausar
              </a>
            }
            @if (actual.estado === 'activo' || actual.estado === 'pausado' || actual.estado === 'borrador') {
              <a
                [routerLink]="['/evaluaciones/ciclos', actual.id, 'reprogramar']"
                class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Reprogramar
              </a>
            }
            @if (actual.estado !== 'cancelado' && actual.estado !== 'cerrado') {
              <a
                [routerLink]="['/evaluaciones/ciclos', actual.id, 'cancelar']"
                class="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Cancelar
              </a>
            }
          </div>
        }
      </div>

      <dl class="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-5">
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Participantes</dt>
          <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ progreso().total }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Autoevaluaciones</dt>
          <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ progreso().auto }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Supervisor</dt>
          <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ progreso().supervisor }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Firmadas</dt>
          <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ progreso().firmadas }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Sin evaluador</dt>
          <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ progreso().sinEvaluador }}</dd>
        </div>
      </dl>

      @if (actual.criterios_generales) {
        <section class="mt-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 class="text-lg font-semibold text-slate-900">Criterios generales</h2>
          <p class="mt-2 whitespace-pre-line text-sm text-slate-600">{{ actual.criterios_generales }}</p>
        </section>
      }

      @if (sinEvaluador().length) {
        <section class="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:p-6">
          <h2 class="text-lg font-semibold text-amber-900">Participantes sin evaluador</h2>
          <p class="mt-1 text-sm text-amber-800">El ciclo se activó igual. Asigná un evaluador acá para que puedan continuar.</p>
          <ul class="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-900">
            @for (ev of sinEvaluador(); track ev.id) {
              <li>{{ nombrePersona(ev.evaluado) }} · {{ ev.puesto_nombre }}</li>
            }
          </ul>
        </section>
      }

      @if (puedeGestionar() && actual.estado === 'borrador') {
        <section class="mt-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 class="text-lg font-semibold text-slate-900">Editar borrador</h2>
          @if (errores().generales.length) {
            <ul class="mt-4 space-y-2">
              @for (error of errores().generales; track error) {
                <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
              }
            </ul>
          }
          <form class="mt-4 space-y-4" [formGroup]="form" (ngSubmit)="guardarBorrador()">
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-nombre">Nombre</label>
                <input id="edit-nombre" type="text" formControlName="nombre" [class]="inputCss" />
                @if (mensajes('nombre'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-inicio">Inicio</label>
                <input id="edit-inicio" type="date" formControlName="fecha_inicio" [class]="inputCss" />
                @if (mensajes('fecha_inicio'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-cierre">Cierre</label>
                <input id="edit-cierre" type="date" formControlName="fecha_cierre" [class]="inputCss" />
                @if (mensajes('fecha_cierre'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-plantilla">Plantilla</label>
                <select id="edit-plantilla" formControlName="plantilla_default" [class]="inputCss">
                  <option [ngValue]="null">— Elegir plantilla —</option>
                  @for (plantilla of plantillasVisibles(); track plantilla.id) {
                    <option [ngValue]="plantilla.id">{{ plantilla.nombre }}</option>
                  }
                </select>
                @if (mensajes('plantilla_default'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-areas">Áreas</label>
                <select id="edit-areas" multiple size="6" formControlName="areas" [class]="inputCss + ' min-h-32'">
                  @for (area of areasVisibles(); track area.id) {
                    <option [ngValue]="area.id">{{ area.nombre }}</option>
                  }
                </select>
                @if (mensajes('areas'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="edit-criterios">Criterios generales</label>
                <textarea id="edit-criterios" rows="4" formControlName="criterios_generales" [class]="textareaCss"></textarea>
                @if (mensajes('criterios_generales'); as lista) {
                  @if (lista.length) {
                    <ul class="errorlist">
                      @for (error of lista; track error) { <li>{{ error }}</li> }
                    </ul>
                  }
                }
              </div>
            </div>
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
              Guardar cambios
            </button>
          </form>
        </section>
      }

      <section class="mt-6">
        <h2 class="text-lg font-semibold text-slate-900">Participantes</h2>
        <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table class="min-w-full text-left text-sm">
            <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th class="px-4 py-3 font-medium">Evaluado</th>
                <th class="px-4 py-3 font-medium">Puesto</th>
                <th class="px-4 py-3 font-medium">Evaluador</th>
                <th class="px-4 py-3 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (ev of participantes(); track ev.id) {
                <tr>
                  <td class="px-4 py-3 font-medium text-slate-900">{{ nombrePersona(ev.evaluado) }}</td>
                  <td class="px-4 py-3 text-slate-600">{{ ev.puesto_nombre }}</td>
                  <td class="px-4 py-3 text-slate-600">
                    @if (puedeReasignar(ev)) {
                      <form class="flex flex-wrap items-center gap-2" (ngSubmit)="asignar(ev)">
                        <label class="sr-only" [attr.for]="'evaluador-' + ev.id">Evaluador</label>
                        <select
                          [id]="'evaluador-' + ev.id"
                          [class]="inputCss"
                          [value]="elegidos()[ev.id] ?? ''"
                          (change)="elegirEvaluador(ev.id, $event)"
                        >
                          <option value="">— Elegir evaluador —</option>
                          @for (candidato of ev.candidatos; track candidato.id) {
                            <option [value]="candidato.id">{{ candidato.nombre }}</option>
                          }
                        </select>
                        <button type="submit" class="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700">
                          Asignar
                        </button>
                      </form>
                    } @else if (ev.sin_evaluador) {
                      <span class="text-amber-800">Sin evaluador</span>
                    } @else {
                      {{ nombrePersona(ev.evaluador) }}
                    }
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap items-center gap-2">
                      <app-badge-estado [estado]="ev.estado" contexto="evaluacion" [etiqueta]="ev.estado_display" [conObservacion]="!!ev.con_observacion" />
                      @if (ev.comparacion_revelada && puedeGestionar()) {
                        <a [routerLink]="['/evaluaciones', ev.id, 'resultado']" class="text-xs font-medium text-sky-700 hover:text-sky-900">
                          Ver
                        </a>
                      }
                    </div>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4" class="px-4 py-8 text-center text-slate-500">
                    Todavía no hay participantes. Activá el ciclo para generarlos.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    }
  `,
})
export class CicloDetallePage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  private readonly title = inject(Title);

  readonly inputCss = INPUT_CSS;
  readonly textareaCss = TEXTAREA_CSS;
  readonly fecha = fechaCorta;

  ciclo = signal<CicloApi | null>(null);
  participantes = signal<ParticipanteVista[]>([]);
  plantillas = signal<PlantillaApi[]>([]);
  areas = signal<AreaOpcion[]>([]);
  vista = signal<'detalle' | 'reprogramar' | 'confirmar'>('detalle');
  confirmacion = signal<ConfirmacionCiclo | null>(null);
  errores = signal<ErroresApi>(erroresVacios());
  erroresFecha = signal<ErroresApi>(erroresVacios());
  elegidos = signal<Record<number, number | null>>({});

  puedeGestionar = computed(() => esGestion(this.auth.sesion()?.usuario.rol));
  progreso = computed(() => progresoCiclo(this.participantes()));
  sinEvaluador = computed(() => this.participantes().filter((item) => item.sin_evaluador));
  plantillasVisibles = computed(() => {
    const actual = this.ciclo()?.plantilla_default;
    return this.plantillas().filter((item) => item.activa || item.id === actual);
  });
  areasVisibles = computed(() => {
    const elegidas = new Set(this.ciclo()?.areas ?? []);
    return this.areas().filter((item) => item.activa || elegidas.has(item.id));
  });

  form = new FormGroup({
    nombre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    fecha_inicio: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    fecha_cierre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    plantilla_default: new FormControl<number | null>(null, { validators: [Validators.required] }),
    areas: new FormControl<number[]>([], { nonNullable: true }),
    criterios_generales: new FormControl('', { nonNullable: true }),
  });

  fechas = new FormGroup({
    fecha_inicio: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    fecha_cierre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  });

  constructor() {
    this.aplicarAccion();
    this.route.paramMap.subscribe((params) => {
      const id = params.get('id');
      if (id) {
        this.cargar(id);
      }
    });
  }

  nombrePersona(persona: ParticipanteApi['evaluado']): string {
    return persona?.nombre || persona?.email || '—';
  }

  puedeReasignar(ev: ParticipanteVista): boolean {
    return this.puedeGestionar() && this.ciclo()?.estado === 'activo' && ev.sin_evaluador;
  }

  mensajes(campo: string): string[] {
    return this.mensajesDe(this.errores(), this.form, campo);
  }

  mensajesFecha(campo: string): string[] {
    return this.mensajesDe(this.erroresFecha(), this.fechas, campo);
  }

  private accionRuta(): string | null {
    const partes = this.router.url.split('?')[0].split('/').filter(Boolean);
    return partes[3] ?? null;
  }

  private aplicarAccion(): void {
    const ciclo = this.ciclo();
    const accion = this.accionRuta();
    if (accion === 'reprogramar') {
      if (ciclo) {
        this.fechas.reset({
          fecha_inicio: ciclo.fecha_inicio.slice(0, 10),
          fecha_cierre: ciclo.fecha_cierre.slice(0, 10),
        });
        this.erroresFecha.set(erroresVacios());
        this.title.setTitle(`Reprogramar ${ciclo.nombre} · TeamPulse`);
      }
      this.vista.set('reprogramar');
      return;
    }
    if (accion === 'activar' || accion === 'pausar' || accion === 'cancelar') {
      if (ciclo) {
        const texto = TEXTOS[accion];
        this.confirmacion.set({
          accion,
          titulo: texto.titulo,
          mensaje: texto.mensaje(ciclo.nombre),
          confirmacion: texto.confirmacion,
          peligro: texto.peligro,
        });
        this.title.setTitle(`${texto.titulo} · TeamPulse`);
      }
      this.vista.set('confirmar');
      return;
    }
    this.vista.set('detalle');
    if (ciclo) {
      this.title.setTitle(`${ciclo.nombre} · TeamPulse`);
    }
  }

  volverDetalle(): void {
    const ciclo = this.ciclo();
    if (ciclo) {
      void this.router.navigate(['/evaluaciones/ciclos', ciclo.id]);
    }
  }

  elegirEvaluador(id: number, event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.elegidos.update((mapa) => ({ ...mapa, [id]: value ? Number(value) : null }));
  }

  asignar(ev: ParticipanteVista): void {
    const evaluador = this.elegidos()[ev.id];
    if (!evaluador) {
      this.alertas.error('Seleccioná un evaluador válido.');
      return;
    }
    this.http.post(`${API}/evaluaciones/${ev.id}/reasignar/`, { evaluador }).subscribe({
      next: () => {
        this.alertas.success('Evaluador asignado.');
        const id = this.ciclo()?.id;
        if (id) {
          this.cargar(String(id));
        }
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  guardarBorrador(): void {
    const ciclo = this.ciclo();
    if (!ciclo) {
      return;
    }
    this.form.markAllAsTouched();
    const raw = this.form.getRawValue();
    const errores = erroresVacios();
    if (raw.fecha_inicio && raw.fecha_cierre && raw.fecha_cierre < raw.fecha_inicio) {
      errores.campos['fecha_cierre'] = ['La fecha de cierre no puede ser anterior al inicio.'];
    }
    this.errores.set(errores);
    if (this.form.invalid || errores.campos['fecha_cierre']) {
      return;
    }
    this.http
      .patch<CicloApi>(`${API}/ciclos/${ciclo.id}/`, {
        nombre: raw.nombre,
        fecha_inicio: raw.fecha_inicio,
        fecha_cierre: raw.fecha_cierre,
        plantilla_default: Number(raw.plantilla_default),
        areas: (raw.areas ?? []).map((id) => Number(id)),
        criterios_generales: raw.criterios_generales,
      })
      .subscribe({
        next: () => {
          this.alertas.success('Ciclo actualizado.');
          this.cargar(String(ciclo.id));
        },
        error: (err) => {
          const parsed = parsearErrores(err);
          if (parsed.generales.length && !Object.keys(parsed.campos).length) {
            this.alertas.error(parsed.generales.join(' '));
          }
          this.errores.set(parsed);
        },
      });
  }

  guardarFechas(): void {
    const ciclo = this.ciclo();
    if (!ciclo) {
      return;
    }
    this.fechas.markAllAsTouched();
    const raw = this.fechas.getRawValue();
    const errores = erroresVacios();
    if (raw.fecha_inicio && raw.fecha_cierre && raw.fecha_cierre < raw.fecha_inicio) {
      errores.campos['fecha_cierre'] = ['La fecha de cierre no puede ser anterior al inicio.'];
    }
    this.erroresFecha.set(errores);
    if (this.fechas.invalid || errores.campos['fecha_cierre']) {
      return;
    }
    this.http
      .post<CicloApi>(`${API}/ciclos/${ciclo.id}/reprogramar/`, {
        fecha_inicio: raw.fecha_inicio,
        fecha_cierre: raw.fecha_cierre,
      })
      .subscribe({
        next: () => {
          this.alertas.success('Las fechas del ciclo se actualizaron.');
          void this.router.navigate(['/evaluaciones/ciclos', ciclo.id]);
        },
        error: (err) => {
          this.alertas.error(mensajeError(err));
          const parsed = parsearErrores(err);
          this.erroresFecha.set(parsed);
        },
      });
  }

  ejecutar(): void {
    const ciclo = this.ciclo();
    const pedido = this.confirmacion();
    if (!ciclo || !pedido) {
      return;
    }
    this.http.post<CicloApi>(`${API}/ciclos/${ciclo.id}/${pedido.accion}/`, {}).subscribe({
      next: (actualizado) => {
        if (pedido.accion === 'activar') {
          const cantidad = actualizado.sin_evaluador_count ?? 0;
          const extra = cantidad > 0 ? ` ${cantidad} participante(s) sin evaluador asignado.` : '';
          this.alertas.success(`El ciclo se activó y se generaron las evaluaciones.${extra}`);
        } else if (pedido.accion === 'pausar') {
          this.alertas.success('El ciclo fue pausado.');
        } else {
          this.alertas.success('El ciclo fue cancelado.');
        }
        void this.router.navigate(['/evaluaciones/ciclos', ciclo.id]);
      },
      error: (err) => {
        this.alertas.error(mensajeError(err));
        this.volverDetalle();
      },
    });
  }

  private cargar(id: string): void {
    if (!this.auth.sesion()) {
      this.auth.loadMe().subscribe(() => this.traerCiclo(id));
      return;
    }
    this.traerCiclo(id);
  }

  private traerCiclo(id: string): void {
    forkJoin({
      ciclo: this.http.get<CicloApi>(`${API}/ciclos/${id}/`),
      participantes: this.http.get<ParticipanteApi[]>(`${API}/ciclos/${id}/participantes/`),
      plantillas: listarTodo<PlantillaApi>(this.http, `${API}/plantillas/`),
      areas: listarTodo<AreaOpcion>(this.http, `${API}/areas/`),
    }).subscribe({
      next: ({ ciclo, participantes, plantillas, areas }) => {
        this.ciclo.set(ciclo);
        this.plantillas.set(plantillas);
        this.areas.set(areas);
        this.form.reset({
          nombre: ciclo.nombre,
          fecha_inicio: ciclo.fecha_inicio.slice(0, 10),
          fecha_cierre: ciclo.fecha_cierre.slice(0, 10),
          plantilla_default: ciclo.plantilla_default,
          areas: ciclo.areas ?? [],
          criterios_generales: ciclo.criterios_generales ?? '',
        });
        this.errores.set(erroresVacios());
        this.aplicarAccion();
        const ordenados = ordenarParticipantes(participantes);
        const reasignar = ordenados.filter(
          (item) => esGestion(this.auth.sesion()?.usuario.rol) && ciclo.estado === 'activo' && item.sin_evaluador,
        );
        if (!reasignar.length) {
          this.participantes.set(ordenados.map((item) => ({ ...item, candidatos: [] })));
          return;
        }
        forkJoin(
          reasignar.map((item) =>
            this.http.get<CandidatoEvaluador[]>(`${API}/evaluaciones/${item.id}/reasignar/`).pipe(
              catchError(() => of([] as CandidatoEvaluador[])),
              map((candidatos) => ({ id: item.id, candidatos })),
            ),
          ),
        ).subscribe((listas) => {
          const mapa = new Map(listas.map((item) => [item.id, item.candidatos]));
          this.participantes.set(ordenados.map((item) => ({ ...item, candidatos: mapa.get(item.id) ?? [] })));
        });
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  private mensajesDe(errores: ErroresApi, form: FormGroup, campo: string): string[] {
    const servidor = errores.campos[campo] ?? [];
    if (servidor.length) {
      return servidor;
    }
    const control = form.get(campo);
    if (control?.touched && control.hasError('required')) {
      return ['Este campo es obligatorio.'];
    }
    return [];
  }
}
