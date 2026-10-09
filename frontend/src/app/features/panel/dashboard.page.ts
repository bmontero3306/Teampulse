import { NgTemplateOutlet } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';

interface CicloActivo {
  id: number;
  nombre: string;
  fecha_inicio: string;
  fecha_cierre: string;
}

interface Kpis {
  participantes: number;
  auto: number;
  supervisor: number;
  firmadas: number;
  sin_evaluador: number;
}

interface Pendiente {
  evaluacion_id: number;
  accion: string;
  href: string;
  estado: string;
  ciclo: string;
}

interface AccesoRapido {
  clave: string;
  etiqueta: string;
  href: string;
}

interface EquipoEvaluacion {
  id: number;
  evaluado: string;
  estado: string;
  estado_display: string;
}

interface Equipo {
  total: number;
  completitud: number;
  alertas_sin_auto: { id: number; evaluado: string }[];
  evaluaciones: EquipoEvaluacion[];
}

interface EmpresaPlataforma {
  id: number;
  nombre: string;
  estado: string;
}

interface Dashboard {
  ciclo_activo: CicloActivo | null;
  kpis: Kpis | null;
  pendientes: Pendiente[];
  accesos_rapidos: AccesoRapido[];
  equipo: Equipo | null;
  empresas_plataforma: EmpresaPlataforma[];
  mostrar_pendientes: boolean;
  mostrar_equipo: boolean;
  mostrar_kpis: boolean;
  mostrar_empresas: boolean;
}

interface EstadoVacio {
  titulo: string;
  mensaje: string;
  accionHref?: string;
  accionLabel?: string;
}

interface BadgeEstado {
  clases: string;
  texto: string;
}

const KPIS_VACIOS: Kpis = {
  participantes: 0,
  auto: 0,
  supervisor: 0,
  firmadas: 0,
  sin_evaluador: 0,
};

const EQUIPO_VACIO: Equipo = {
  total: 0,
  completitud: 0,
  alertas_sin_auto: [],
  evaluaciones: [],
};

/** Abreviaturas de django/conf/locale/es_AR, formato DATE_FORMAT = "j N Y". */
const MESES_AP = [
  '',
  'Enero',
  'Feb.',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Ago.',
  'Set.',
  'Oct.',
  'Nov.',
  'Dic.',
];

const BADGE_EMERALD =
  'inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200';
const BADGE_AMBER =
  'inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200';
const BADGE_RED =
  'inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200';
const BADGE_SLATE =
  'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200';

const ETIQUETAS_EVALUACION: Record<string, string> = {
  pendiente_auto: 'Pendiente de autoevaluación',
  auto_borrador: 'Autoevaluación en borrador',
  auto_completa: 'Autoevaluación completa',
  supervisor_borrador: 'Evaluación de supervisor en borrador',
  pendiente_comparacion: 'Pendiente de comparación',
  pendiente_conformidad: 'Pendiente de conformidad',
  cerrada: 'Cerrada',
  cerrada_con_obs: 'Cerrada con observación',
  pausado: 'Pausado',
  cancelada: 'Cancelada',
  cancelado: 'Cancelada',
  activa: 'Activa',
};

const ETIQUETAS_EMPRESA: Record<string, string> = {
  activa: 'Activa',
  suspendida: 'Suspendida',
  inactiva: 'Inactiva',
};

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, NgTemplateOutlet],
  template: `
    <section>
      <header class="mb-6">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Panel</h1>
        <p class="mt-1 text-sm text-slate-600">
          @if (rol(); as nombreRol) {
            Vista de {{ nombreRol }}.
          }
          <a routerLink="/ayuda" class="text-sky-700 hover:text-sky-900">Guías del proceso</a>
        </p>
        @if (data(); as panel) {
          @if (panel.ciclo_activo; as ciclo) {
            <p class="mt-2 text-sm text-slate-700">
              Ciclo activo: <span class="font-medium">{{ ciclo.nombre }}</span>
              <span class="text-slate-500">({{ fecha(ciclo.fecha_inicio) }} – {{ fecha(ciclo.fecha_cierre) }})</span>
            </p>
          } @else if (!panel.mostrar_empresas) {
            <p class="mt-2 text-sm text-slate-500">No hay ciclo activo.</p>
          }
        }
      </header>

      @if (data(); as panel) {
        <div class="grid gap-6">
          @if (panel.mostrar_empresas) {
            <article data-widget="empresas" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 class="text-lg font-semibold text-slate-900">Empresas de la plataforma</h2>
                  <p class="mt-1 text-sm text-slate-500">
                    Estado de cada tenant. El alta y la edición viven en el módulo de empresas.
                  </p>
                </div>
                <a routerLink="/empresas" class="text-sm font-medium text-sky-700 hover:text-sky-800">
                  Gestionar empresas
                </a>
              </div>

              @if (panel.empresas_plataforma.length) {
                <div class="mt-4 overflow-x-auto">
                  <table class="min-w-[28rem] w-full text-left text-sm">
                    <thead class="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th class="py-2 pr-4 font-medium">Nombre</th>
                        <th class="py-2 pr-4 font-medium">Estado</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      @for (emp of panel.empresas_plataforma; track emp.id) {
                        <tr>
                          <td class="py-2 pr-4">
                            <a routerLink="/empresas" class="font-medium text-sky-700 hover:text-sky-800">
                              {{ emp.nombre }}
                            </a>
                          </td>
                          <td class="py-2 pr-4">
                            @if (emp.estado === 'activa') {
                              <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">
                                {{ etiquetaEmpresa(emp.estado) }}
                              </span>
                            } @else if (emp.estado === 'suspendida') {
                              <span class="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-800">
                                {{ etiquetaEmpresa(emp.estado) }}
                              </span>
                            } @else {
                              <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                {{ etiquetaEmpresa(emp.estado) }}
                              </span>
                            }
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else {
                <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                  <ng-container
                    [ngTemplateOutlet]="estadoVacio"
                    [ngTemplateOutletContext]="
                      vacio(
                        'Todavía no hay empresas registradas',
                        'Cuando se den de alta empresas, van a aparecer en este listado.',
                        '/empresas',
                        'Ir a empresas'
                      )
                    "
                  />
                </div>
              }
            </article>
          }

          @if (panel.mostrar_kpis) {
            <article data-widget="kpis" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 class="text-lg font-semibold text-slate-900">Ciclo de evaluación</h2>
                  <p class="mt-1 text-sm text-slate-500">Indicadores del ciclo activo de la empresa.</p>
                </div>
                @if (panel.ciclo_activo) {
                  <span class="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-800">Activo</span>
                } @else {
                  <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">Sin ciclo</span>
                }
              </div>

              @if (!panel.ciclo_activo) {
                <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                  <ng-container
                    [ngTemplateOutlet]="estadoVacio"
                    [ngTemplateOutletContext]="
                      vacio(
                        'No hay ciclo activo',
                        'Los indicadores se van a completar cuando haya un ciclo activo.'
                      )
                    "
                  />
                </div>
              }

              <dl class="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-5">
                <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Participantes</dt>
                  <dd data-kpi="participantes" class="mt-1 text-2xl font-semibold text-slate-900">
                    {{ kpisDe(panel).participantes }}
                  </dd>
                </div>
                <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Autoevaluaciones</dt>
                  <dd data-kpi="auto" class="mt-1 text-2xl font-semibold text-slate-900">{{ kpisDe(panel).auto }}</dd>
                </div>
                <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Supervisor</dt>
                  <dd data-kpi="supervisor" class="mt-1 text-2xl font-semibold text-slate-900">
                    {{ kpisDe(panel).supervisor }}
                  </dd>
                </div>
                <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Firmadas</dt>
                  <dd data-kpi="firmadas" class="mt-1 text-2xl font-semibold text-slate-900">
                    {{ kpisDe(panel).firmadas }}
                  </dd>
                </div>
                <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Sin evaluador</dt>
                  <dd data-kpi="sin_evaluador" class="mt-1 text-2xl font-semibold text-slate-900">
                    {{ kpisDe(panel).sin_evaluador }}
                  </dd>
                </div>
              </dl>
            </article>
          }

          @if (panel.mostrar_equipo) {
            <article data-widget="equipo" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 class="text-lg font-semibold text-slate-900">Mi equipo</h2>
                  <p class="mt-1 text-sm text-slate-500">Colaboradores a cargo y avance de sus evaluaciones.</p>
                </div>
                <a routerLink="/evaluaciones/equipo" class="text-sm font-medium text-sky-700 hover:text-sky-800">
                  Ver equipo
                </a>
              </div>

              @if (!panel.ciclo_activo) {
                <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                  <ng-container
                    [ngTemplateOutlet]="estadoVacio"
                    [ngTemplateOutletContext]="
                      vacio(
                        'No hay colaboradores para evaluar',
                        'Cuando haya un ciclo activo, acá vas a ver el avance de tu equipo.'
                      )
                    "
                  />
                </div>
              } @else {
                <dl class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Equipo</dt>
                    <dd data-equipo="total" class="mt-1 text-2xl font-semibold text-slate-900">
                      {{ equipoDe(panel).total }}
                    </dd>
                  </div>
                  <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Completitud</dt>
                    <dd data-equipo="completitud" class="mt-1 text-2xl font-semibold text-slate-900">
                      {{ equipoDe(panel).completitud }}%
                    </dd>
                  </div>
                  <div class="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3">
                    <dt class="text-xs font-medium uppercase tracking-wide text-amber-700">Sin autoevaluación</dt>
                    <dd data-equipo="sin-auto" class="mt-1 text-2xl font-semibold text-amber-900">
                      {{ equipoDe(panel).alertas_sin_auto.length }}
                    </dd>
                  </div>
                </dl>

                @if (equipoDe(panel).alertas_sin_auto.length) {
                  <div class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3" data-alerta="sin-autoevaluacion">
                    <p class="text-sm font-medium text-amber-900">Alertas: sin autoevaluación</p>
                    <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                      @for (ev of equipoDe(panel).alertas_sin_auto; track ev.id) {
                        <li>{{ ev.evaluado }}</li>
                      }
                    </ul>
                  </div>
                }

                @if (equipoDe(panel).evaluaciones.length) {
                  <div class="mt-4 overflow-x-auto">
                    <table class="min-w-[36rem] w-full text-left text-sm">
                      <thead class="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                          <th class="py-2 pr-4 font-medium">Colaborador</th>
                          <th class="py-2 pr-4 font-medium">Estado</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-100">
                        @for (item of equipoDe(panel).evaluaciones; track item.id) {
                          <tr>
                            <td class="py-2 pr-4 text-slate-800">{{ item.evaluado }}</td>
                            <td class="py-2 pr-4">
                              @let badge = badgeEvaluacion(item.estado, item.estado_display);
                              <span [class]="badge.clases">{{ badge.texto }}</span>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                } @else {
                  <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                    <ng-container
                      [ngTemplateOutlet]="estadoVacio"
                      [ngTemplateOutletContext]="
                        vacio(
                          'No hay colaboradores para evaluar',
                          'Todavía no hay evaluaciones asignadas a tu equipo.'
                        )
                      "
                    />
                  </div>
                }
              }
            </article>
          }

          @if (panel.mostrar_pendientes) {
            <article data-widget="pendientes" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 class="text-lg font-semibold text-slate-900">Mis pendientes</h2>
                  <p class="mt-1 text-sm text-slate-500">Autoevaluaciones y firmas que tenés que completar.</p>
                </div>
                <a routerLink="/evaluaciones/mias" class="text-sm font-medium text-sky-700 hover:text-sky-800">
                  Ver mis evaluaciones
                </a>
              </div>

              @if (panel.accesos_rapidos.length) {
                <div class="mt-4 flex flex-wrap gap-2">
                  @for (acceso of panel.accesos_rapidos; track acceso.clave) {
                    <a
                      [attr.data-acceso]="acceso.clave"
                      [routerLink]="ruta(acceso.href)"
                      class="inline-flex rounded-lg border border-sky-200 bg-sky-50 px-3 py-1.5 text-sm font-medium text-sky-800 hover:bg-sky-100"
                    >
                      {{ acceso.etiqueta }}
                    </a>
                  }
                </div>
              }

              @if (!panel.ciclo_activo) {
                <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                  <ng-container
                    [ngTemplateOutlet]="estadoVacio"
                    [ngTemplateOutletContext]="
                      vacio(
                        'No hay ciclo activo',
                        'Cuando RRHH active un ciclo, vas a ver tus evaluaciones pendientes acá.'
                      )
                    "
                  />
                </div>
              } @else if (panel.pendientes.length) {
                <div class="mt-4 overflow-x-auto">
                  <table class="min-w-[36rem] w-full text-left text-sm">
                    <thead class="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th class="py-2 pr-4 font-medium">Evaluación</th>
                        <th class="py-2 pr-4 font-medium">Estado</th>
                        <th class="py-2 font-medium">Acción</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      @for (item of panel.pendientes; track item.evaluacion_id) {
                        <tr>
                          <td class="py-2 pr-4 text-slate-800">{{ etiquetaEvaluacion(item) }}</td>
                          <td class="py-2 pr-4">
                            @let badge = badgeEvaluacion(item.estado);
                            <span [class]="badge.clases">{{ badge.texto }}</span>
                          </td>
                          <td class="py-2 whitespace-nowrap">
                            <a [routerLink]="ruta(item.href)" class="font-medium text-sky-700 hover:text-sky-800">
                              {{ item.accion }}
                            </a>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else {
                <div class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6">
                  <ng-container
                    [ngTemplateOutlet]="estadoVacio"
                    [ngTemplateOutletContext]="
                      vacio(
                        'Sin pendientes',
                        'No tenés autoevaluaciones ni firmas pendientes en este momento.'
                      )
                    "
                  />
                </div>
              }
            </article>
          }
        </div>
      }
    </section>

    <ng-template
      #estadoVacio
      let-titulo="titulo"
      let-mensaje="mensaje"
      let-accionHref="accionHref"
      let-accionLabel="accionLabel"
    >
      @if (titulo) {
        <p class="text-sm font-medium text-slate-800">{{ titulo }}</p>
      }
      <p class="mt-1 text-sm text-slate-500">{{ mensaje }}</p>
      @if (accionHref && accionLabel) {
        <a
          [routerLink]="accionHref"
          class="mt-3 inline-flex rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
        >
          {{ accionLabel }}
        </a>
      }
    </ng-template>
  `,
})
export class DashboardPage {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  data = signal<Dashboard | null>(null);

  constructor() {
    this.http.get<Dashboard>(`${API}/dashboard/`).subscribe((panel) => this.data.set(panel));
  }

  rol(): string {
    return this.auth.sesion()?.usuario.rol_display ?? '';
  }

  fecha(iso: string): string {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!match) {
      return iso;
    }
    const dia = Number(match[3]);
    const mes = MESES_AP[Number(match[2])] ?? match[2];
    return `${dia} ${mes} ${match[1]}`;
  }

  kpisDe(panel: Dashboard): Kpis {
    return panel.kpis ?? KPIS_VACIOS;
  }

  equipoDe(panel: Dashboard): Equipo {
    return panel.equipo ?? EQUIPO_VACIO;
  }

  etiquetaEmpresa(estado: string): string {
    return ETIQUETAS_EMPRESA[estado] ?? estado;
  }

  etiquetaEvaluacion(item: Pendiente): string {
    const email = this.auth.sesion()?.usuario.email;
    return email ? `${email} · ${item.ciclo}` : item.ciclo;
  }

  badgeEvaluacion(estado: string, etiqueta?: string): BadgeEstado {
    const texto = etiqueta || ETIQUETAS_EVALUACION[estado] || estado;
    if (estado === 'cerrada') {
      return { clases: BADGE_EMERALD, texto: 'Cerrada' };
    }
    if (estado === 'cerrada_con_obs') {
      return { clases: BADGE_RED, texto: 'Cerrada con observación' };
    }
    if (estado === 'pendiente_auto') {
      return { clases: BADGE_AMBER, texto: 'Pendiente de autoevaluación' };
    }
    if (estado === 'pendiente_comparacion') {
      return { clases: BADGE_AMBER, texto: 'Pendiente de comparación' };
    }
    if (estado === 'pendiente_conformidad') {
      return { clases: BADGE_AMBER, texto: 'Pendiente de conformidad' };
    }
    if (estado === 'pausado' || estado === 'auto_borrador' || estado === 'supervisor_borrador') {
      return { clases: BADGE_AMBER, texto };
    }
    if (estado === 'cancelada' || estado === 'cancelado') {
      return { clases: BADGE_RED, texto: 'Cancelada' };
    }
    if (estado === 'activa') {
      return { clases: BADGE_EMERALD, texto: 'Activa' };
    }
    return { clases: BADGE_SLATE, texto };
  }

  vacio(titulo: string, mensaje: string, accionHref = '', accionLabel = ''): EstadoVacio {
    return { titulo, mensaje, accionHref, accionLabel };
  }

  ruta(href: string): string {
    return href.length > 1 && href.endsWith('/') ? href.slice(0, -1) : href;
  }
}
