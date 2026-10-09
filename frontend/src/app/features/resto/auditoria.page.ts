// Alineada a auditoria/templates/auditoria/lista.html.
// La ruta /auditoria sigue cargando AuditoriaPage desde resto.pages.ts.
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';

interface LogAudit {
  id: number;
  created_at: string;
  usuario_email: string | null;
  accion_display: string;
  modelo: string;
  object_id: string;
  payload: unknown;
  ip: string | null;
  user_agent: string;
}

interface RespuestaAudit {
  pagina: Pagina<LogAudit>;
  acciones: string[];
  modelos: string[];
  usuarios: { id: number; email: string }[];
}

const PAGE_SIZE = 25;
const CAMPO =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';
const ZONA = 'America/Argentina/Buenos_Aires';

const ACCION_LABELS: Record<string, string> = {
  login: 'Inicio de sesión',
  logout: 'Cierre de sesión',
  login_fallido: 'Login fallido',
  crear: 'Alta',
  editar: 'Edición',
  eliminar: 'Eliminación',
  desactivar: 'Desactivación',
  suspender: 'Suspensión',
  activar: 'Activación',
  exportar: 'Exportación',
  firmar: 'Firma',
};

function fechaAuditoria(iso: string): string {
  const fmt = new Intl.DateTimeFormat('es-AR', {
    timeZone: ZONA,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  });
  const partes: Record<string, string> = {};
  for (const parte of fmt.formatToParts(new Date(iso))) {
    if (parte.type !== 'literal') {
      partes[parte.type] = parte.value;
    }
  }
  return `${partes['day']}/${partes['month']}/${partes['year']} ${partes['hour']}:${partes['minute']}:${partes['second']}`;
}

@Component({
  selector: 'app-auditoria',
  template: `
    <section>
      <div class="mb-6">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Auditoría</h1>
        <p class="mt-1 text-sm text-slate-600">
          Trazabilidad de altas, ediciones, inicios de sesión y demás acciones de la empresa.
        </p>
      </div>

      <form class="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" (submit)="aplicar($event)">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_usuario">Usuario</label>
            <select id="id_usuario" name="usuario" [class]="campo" [value]="usuario()" (change)="usuario.set(valor($event))">
              <option value="">Todos</option>
              @for (op of usuarios(); track op.id) {
                <option [value]="op.id">{{ op.email }}</option>
              }
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_accion">Acción</label>
            <select id="id_accion" name="accion" [class]="campo" [value]="accion()" (change)="accion.set(valor($event))">
              <option value="">Todas</option>
              @for (op of acciones(); track op) {
                <option [value]="op">{{ etiquetaAccion(op) }}</option>
              }
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_modelo">Modelo</label>
            <select id="id_modelo" name="modelo" [class]="campo" [value]="modelo()" (change)="modelo.set(valor($event))">
              <option value="">Todos</option>
              @for (op of modelos(); track op) {
                <option [value]="op">{{ op }}</option>
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
            Filtrar
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

      <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Fecha</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Usuario</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Acción</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Modelo</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">Objeto</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">IP</th>
              <th scope="col" class="min-w-64 px-4 py-3 text-left font-semibold text-slate-700">Detalle</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (log of logs(); track log.id) {
              <tr class="align-top hover:bg-sky-50/50">
                <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ fecha(log.created_at) }}</td>
                <td class="whitespace-nowrap px-4 py-3 text-slate-800">{{ texto(log.usuario_email) }}</td>
                <td class="whitespace-nowrap px-4 py-3">
                  <span class="inline-flex rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-800">
                    {{ log.accion_display }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">{{ texto(log.modelo) }}</td>
                <td class="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">{{ texto(log.object_id) }}</td>
                <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ texto(log.ip) }}</td>
                <td class="px-4 py-3">
                  <details class="group">
                    <summary class="cursor-pointer text-sky-700 hover:text-sky-900">
                      Ver payload
                    </summary>
                    <pre class="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{{ payload(log) }}</pre>
                    @if (log.user_agent) {
                      <p class="mt-2 text-xs text-slate-500">Agente: {{ log.user_agent }}</p>
                    }
                  </details>
                </td>
              </tr>
            } @empty {
              @if (cargada()) {
                <tr>
                  <td colspan="7" class="px-4 py-10 text-center text-slate-500">
                    No hay registros de auditoría para los filtros seleccionados.
                  </td>
                </tr>
              }
            }
          </tbody>
        </table>
      </div>

      @if (paginas() > 1) {
        <nav class="mt-4 flex items-center justify-between text-sm text-slate-600" aria-label="Paginación">
          <span>
            Página {{ page() }} de {{ paginas() }}
          </span>
          <div class="flex gap-2">
            @if (page() > 1) {
              <a class="rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-slate-50" href="" (click)="ir(page() - 1, $event)">Anterior</a>
            }
            @if (page() < paginas()) {
              <a class="rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-slate-50" href="" (click)="ir(page() + 1, $event)">Siguiente</a>
            }
          </div>
        </nav>
      }
    </section>
  `,
})
export class AuditoriaPage {
  private readonly http = inject(HttpClient);
  readonly campo = CAMPO;
  logs = signal<LogAudit[]>([]);
  count = signal(0);
  cargada = signal(false);
  page = signal(1);
  usuarios = signal<{ id: number; email: string }[]>([]);
  acciones = signal<string[]>([]);
  modelos = signal<string[]>([]);
  usuario = signal('');
  accion = signal('');
  modelo = signal('');
  fechaDesde = signal('');
  fechaHasta = signal('');

  constructor() {
    inject(Title).setTitle('Auditoría · TeamPulse');
    this.cargar();
  }

  paginas(): number {
    return Math.max(1, Math.ceil(this.count() / PAGE_SIZE));
  }

  valor(event: Event): string {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }

  fecha(iso: string): string {
    return fechaAuditoria(iso);
  }

  texto(valor: string | null | undefined): string {
    return valor ? valor : '—';
  }

  etiquetaAccion(codigo: string): string {
    return ACCION_LABELS[codigo] ?? codigo;
  }

  payload(log: LogAudit): string {
    const valor = log.payload;
    if (valor == null || valor === '') {
      return '{}';
    }
    if (typeof valor === 'string') {
      return valor;
    }
    return JSON.stringify(valor, null, 2);
  }

  aplicar(event: Event): void {
    event.preventDefault();
    this.page.set(1);
    this.cargar();
  }

  limpiar(event: Event): void {
    event.preventDefault();
    this.usuario.set('');
    this.accion.set('');
    this.modelo.set('');
    this.fechaDesde.set('');
    this.fechaHasta.set('');
    this.page.set(1);
    this.cargar();
  }

  ir(pagina: number, event: Event): void {
    event.preventDefault();
    this.page.set(pagina);
    this.cargar();
  }

  private cargar(): void {
    const params: Record<string, string> = {
      page: String(this.page()),
      page_size: String(PAGE_SIZE),
    };
    if (this.usuario()) {
      params['usuario'] = this.usuario();
    }
    if (this.accion()) {
      params['accion'] = this.accion();
    }
    if (this.modelo()) {
      params['modelo'] = this.modelo();
    }
    if (this.fechaDesde()) {
      params['fecha_desde'] = this.fechaDesde();
    }
    if (this.fechaHasta()) {
      params['fecha_hasta'] = this.fechaHasta();
    }
    this.http.get<RespuestaAudit>(`${API}/auditoria/`, { params }).subscribe((data) => {
      this.logs.set(data.pagina.results);
      this.count.set(data.pagina.count);
      this.cargada.set(true);
      this.usuarios.set(data.usuarios);
      this.acciones.set(data.acciones);
      this.modelos.set(data.modelos);
    });
  }
}
