// Alineada a reportes/templates/reportes/iso.html y al badge de evaluaciones/_badge_estado.html.
// La ruta /reportes/iso sigue cargando ReportesPage desde resto.pages.ts.
import { HttpClient, HttpResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';

interface Opcion {
  id: number;
  nombre: string;
}

interface Indicadores {
  total: number;
  auto_completas: number;
  pct_auto: number;
  supervisor: number;
  pct_supervisor: number;
  firmadas: number;
  pct_firmadas: number;
  con_observacion: number;
  pct_observacion: number;
  promedio_auto: string;
  promedio_supervisor: string;
  promedio_firma: string;
}

interface FilaIso {
  id: number;
  ciclo: string;
  evaluado: string;
  evaluador: string | null;
  area: string | null;
  estado: string;
  estado_display: string;
  con_observacion?: boolean;
  enviada_auto_en: string | null;
  cerrada_supervisor_en: string | null;
  firmada_en: string | null;
  firma_hash: string | null;
}

interface ReporteIso {
  empresa: string | null;
  periodo_desde: string | null;
  periodo_hasta: string | null;
  indicadores: Indicadores;
  evaluaciones: FilaIso[];
  opciones: {
    empresas: Opcion[];
    ciclos: Opcion[];
    areas: Opcion[];
  };
}

const CAMPO =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'pendiente_reunion', label: 'Pendiente de reunión' },
  { value: 'pendiente_conformidad', label: 'Pendiente de conformidad' },
  { value: 'cerrada', label: 'Firmada — conforme' },
  { value: 'con_observacion', label: 'Firmada — con observación' },
  { value: 'no_firmada', label: 'Sin firmar' },
];

const ZONA = 'America/Argentina/Buenos_Aires';

function fechaCorta(iso: string | null | undefined): string {
  if (!iso) {
    return '—';
  }
  const fmt = new Intl.DateTimeFormat('es-AR', {
    timeZone: ZONA,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
  const partes: Record<string, string> = {};
  for (const parte of fmt.formatToParts(new Date(iso))) {
    if (parte.type !== 'literal') {
      partes[parte.type] = parte.value;
    }
  }
  return `${partes['day']}/${partes['month']}/${partes['year']} ${partes['hour']}:${partes['minute']}`;
}

function fechaDia(iso: string | null | undefined): string {
  if (!iso) {
    return '';
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) {
    return iso;
  }
  return `${match[3]}/${match[2]}/${match[1]}`;
}

function badgeClase(estado: string, conObservacion = false): string {
  const base = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset';
  if (conObservacion || estado === 'cancelada' || estado === 'cancelado') {
    return `${base} bg-red-50 text-red-800 ring-red-200`;
  }
  if (estado === 'cerrada' || estado === 'activa') {
    return `${base} bg-emerald-50 text-emerald-800 ring-emerald-200`;
  }
  if (
    estado === 'autoevaluacion' ||
    estado === 'evaluacion_supervisor' ||
    estado === 'pendiente_reunion' ||
    estado === 'pendiente_conformidad' ||
    estado === 'pausado'
  ) {
    return `${base} bg-amber-50 text-amber-800 ring-amber-200`;
  }
  return `${base} bg-slate-100 text-slate-700 ring-slate-200`;
}

@Component({
  selector: 'app-reportes',
  template: `
    <section>
      <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Reportes</h1>
          <p class="mt-1 text-sm text-slate-600">
            Cumplimiento del ciclo de evaluación: indicadores, fechas de cada etapa y export auditable.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <a
            href=""
            class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
            (click)="bajar('pdf', $event)"
          >
            Exportar PDF
          </a>
          <a
            href=""
            class="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            (click)="bajar('excel', $event)"
          >
            Exportar Excel
          </a>
        </div>
      </div>

      <form class="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" (submit)="aplicar($event)">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          @if (opciones().empresas.length) {
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700" for="id_empresa">Empresa</label>
              <select id="id_empresa" name="empresa" [class]="campo" [value]="empresa()" (change)="empresa.set(valor($event))">
                <option value="">Seleccioná una empresa</option>
                @for (op of opciones().empresas; track op.id) {
                  <option [value]="op.id">{{ op.nombre }}</option>
                }
              </select>
            </div>
          }
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_ciclo">Ciclo</label>
            <select id="id_ciclo" name="ciclo" [class]="campo" [value]="ciclo()" (change)="ciclo.set(valor($event))">
              <option value="">Todos</option>
              @for (op of opciones().ciclos; track op.id) {
                <option [value]="op.id">{{ op.nombre }}</option>
              }
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_area">Área</label>
            <select id="id_area" name="area" [class]="campo" [value]="area()" (change)="area.set(valor($event))">
              <option value="">Todas</option>
              @for (op of opciones().areas; track op.id) {
                <option [value]="op.id">{{ op.nombre }}</option>
              }
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_estado">Estado de conformidad</label>
            <select id="id_estado" name="estado" [class]="campo" [value]="estado()" (change)="estado.set(valor($event))">
              @for (op of estados; track op.value) {
                <option [value]="op.value">{{ op.label }}</option>
              }
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_fecha_desde">Desde</label>
            <input id="id_fecha_desde" name="fecha_desde" type="date" [class]="campo" [value]="fechaDesde()" (input)="fechaDesde.set(valor($event))" />
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_fecha_hasta">Hasta</label>
            <input id="id_fecha_hasta" name="fecha_hasta" type="date" [class]="campo" [value]="fechaHasta()" (input)="fechaHasta.set(valor($event))" />
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
            Aplicar filtros
          </button>
          <a
            href=""
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            (click)="limpiar($event)"
          >
            Limpiar
          </a>
        </div>
      </form>

      @if (reporte(); as actual) {
        @if (!actual.empresa) {
          <div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-600">
            Seleccioná una empresa para generar el reporte.
          </div>
        } @else {
          <p class="mb-4 text-sm text-slate-600">
            <span class="font-medium text-slate-800">{{ actual.empresa }}</span>
            · Periodo:
            @if (actual.periodo_desde && actual.periodo_hasta) {
              {{ dia(actual.periodo_desde) }} – {{ dia(actual.periodo_hasta) }}
            } @else {
              todos
            }
          </p>

          <dl class="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Total</dt>
              <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ actual.indicadores.total }}</dd>
            </div>
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">% Auto</dt>
              <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ pct(actual.indicadores.pct_auto) }}&nbsp;%</dd>
              <dd class="text-xs text-slate-500">{{ actual.indicadores.auto_completas }} completas</dd>
            </div>
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">% Supervisor</dt>
              <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ pct(actual.indicadores.pct_supervisor) }}&nbsp;%</dd>
              <dd class="text-xs text-slate-500">{{ actual.indicadores.supervisor }} cerradas</dd>
            </div>
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">% Firmadas</dt>
              <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ pct(actual.indicadores.pct_firmadas) }}&nbsp;%</dd>
              <dd class="text-xs text-slate-500">{{ actual.indicadores.firmadas }} firmas</dd>
            </div>
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">% Observación</dt>
              <dd class="mt-1 text-2xl font-semibold text-slate-900">{{ pct(actual.indicadores.pct_observacion) }}&nbsp;%</dd>
              <dd class="text-xs text-slate-500">{{ actual.indicadores.con_observacion }} con obs.</dd>
            </div>
            <div class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Tiempos promedio</dt>
              <dd class="mt-1 text-xs text-slate-700">Auto: {{ actual.indicadores.promedio_auto }}</dd>
              <dd class="text-xs text-slate-700">Supervisor: {{ actual.indicadores.promedio_supervisor }}</dd>
              <dd class="text-xs text-slate-700">Firma: {{ actual.indicadores.promedio_firma }}</dd>
            </div>
          </dl>

          <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table class="min-w-full divide-y divide-slate-200 text-sm">
              <thead class="bg-slate-50">
                <tr>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Evaluado</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Evaluador</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Área</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Ciclo</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Estado</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Auto</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Supervisor</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Firma</th>
                  <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Hash</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (ev of actual.evaluaciones; track ev.id) {
                  <tr class="align-top hover:bg-sky-50/50">
                    <td class="whitespace-nowrap px-4 py-3 font-medium text-slate-900">{{ ev.evaluado }}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-700">{{ ev.evaluador || '—' }}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ ev.area || '—' }}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ ev.ciclo }}</td>
                    <td class="whitespace-nowrap px-4 py-3">
                      <span [class]="badge(ev.estado, !!ev.con_observacion)">{{ ev.estado_display }}</span>
                    </td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ cuando(ev.enviada_auto_en) }}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ cuando(ev.cerrada_supervisor_en) }}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ cuando(ev.firmada_en) }}</td>
                    <td class="px-4 py-3 font-mono text-xs text-slate-600">{{ ev.firma_hash || '—' }}</td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="9" class="px-4 py-10 text-center text-slate-500">
                      No hay evaluaciones para los filtros seleccionados.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      }
    </section>
  `,
})
export class ReportesPage {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  readonly campo = CAMPO;
  readonly estados = ESTADOS;
  reporte = signal<ReporteIso | null>(null);
  opciones = signal<ReporteIso['opciones']>({ empresas: [], ciclos: [], areas: [] });
  empresa = signal('');
  ciclo = signal('');
  area = signal('');
  estado = signal('');
  fechaDesde = signal('');
  fechaHasta = signal('');

  constructor() {
    inject(Title).setTitle('Reportes · TeamPulse');
    const id = this.auth.sesion()?.empresa_actual?.id;
    if (id) {
      this.empresa.set(String(id));
    }
    this.cargar();
  }

  valor(event: Event): string {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }

  pct(valor: number): string {
    return Number(valor ?? 0).toFixed(1).replace('.', ',');
  }

  dia(iso: string | null): string {
    return fechaDia(iso);
  }

  cuando(iso: string | null): string {
    return fechaCorta(iso);
  }

  badge(estado: string, conObservacion = false): string {
    return badgeClase(estado, conObservacion);
  }

  aplicar(event: Event): void {
    event.preventDefault();
    this.cargar();
  }

  limpiar(event: Event): void {
    event.preventDefault();
    const id = this.auth.sesion()?.empresa_actual?.id;
    this.empresa.set(id ? String(id) : '');
    this.ciclo.set('');
    this.area.set('');
    this.estado.set('');
    this.fechaDesde.set('');
    this.fechaHasta.set('');
    this.cargar();
  }

  cargar(): void {
    this.http.get<ReporteIso>(`${API}/reportes/iso/`, { params: this.params() }).subscribe((data) => {
      this.reporte.set(data);
      this.opciones.set(data.opciones);
    });
  }

  bajar(formato: 'pdf' | 'excel', event: Event): void {
    event.preventDefault();
    this.http
      .get(`${API}/reportes/iso/${formato}/`, {
        params: this.params(),
        responseType: 'blob',
        observe: 'response',
      })
      .subscribe((resp) => this.descargar(resp, formato));
  }

  private params(): Record<string, string> {
    const params: Record<string, string> = {};
    if (this.opciones().empresas.length && this.empresa()) {
      params['empresa'] = this.empresa();
    }
    if (this.ciclo()) {
      params['ciclo'] = this.ciclo();
    }
    if (this.area()) {
      params['area'] = this.area();
    }
    if (this.estado()) {
      params['estado'] = this.estado();
    }
    if (this.fechaDesde()) {
      params['fecha_desde'] = this.fechaDesde();
    }
    if (this.fechaHasta()) {
      params['fecha_hasta'] = this.fechaHasta();
    }
    return params;
  }

  private descargar(resp: HttpResponse<Blob>, formato: 'pdf' | 'excel'): void {
    const blob = resp.body;
    if (!blob) {
      return;
    }
    const disposition = resp.headers.get('Content-Disposition') ?? '';
    const encontrado = /filename="([^"]+)"/.exec(disposition);
    const nombre = encontrado?.[1] ?? (formato === 'pdf' ? 'reporte-iso.pdf' : 'reporte-iso.xlsx');
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    enlace.click();
    URL.revokeObjectURL(url);
  }
}
