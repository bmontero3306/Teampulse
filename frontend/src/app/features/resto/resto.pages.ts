import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';
import { AlertService } from '../../shared/alert.service';
import { ButtonComponent } from '../../shared/button.component';
import { DynamicTableComponent } from '../../shared/dynamic-table.component';
import { StatsCardComponent } from '../../shared/stats-card.component';

interface Notificacion {
  id: number;
  titulo: string;
  mensaje: string;
  leida: boolean;
  created_at: string;
  url: string;
}

@Component({
  selector: 'app-notificaciones',
  imports: [ButtonComponent],
  template: `
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Notificaciones</h1>
      <app-button color="secondary" size="sm" label="Marcar todas" (buttonClick)="todas()" />
    </div>
    <ul class="mt-4 divide-y rounded-xl border border-slate-200 bg-white">
      @for (item of lista(); track item.id) {
        <li class="px-4 py-3 text-sm" [class.opacity-60]="item.leida">
          <button type="button" class="text-left" (click)="leer(item)">
            <p class="font-medium">{{ item.titulo }}</p>
            <p class="text-slate-600">{{ item.mensaje }}</p>
          </button>
        </li>
      } @empty { <li class="px-4 py-6 text-slate-500">No hay notificaciones.</li> }
    </ul>
  `,
})
export class NotificacionesPage {
  private readonly http = inject(HttpClient);
  lista = signal<Notificacion[]>([]);
  constructor() {
    this.cargar();
  }
  cargar(): void {
    this.http.get<Pagina<Notificacion>>(`${API}/notificaciones/`).subscribe((p) => this.lista.set(p.results));
  }
  leer(item: Notificacion): void {
    this.http.post(`${API}/notificaciones/${item.id}/leer/`, {}).subscribe(() => this.cargar());
  }
  todas(): void {
    this.http.post(`${API}/notificaciones/leer-todas/`, {}).subscribe(() => this.cargar());
  }
}

@Component({
  selector: 'app-reportes',
  imports: [StatsCardComponent, ButtonComponent, DynamicTableComponent],
  template: `
    <h1 class="text-2xl font-semibold">Reportes</h1>
    <form class="mt-4 flex flex-wrap gap-2" (submit)="$event.preventDefault(); cargar()">
      <select class="rounded-lg border border-slate-300 px-2 py-2 text-sm" (change)="ciclo = valor($event)">
        <option value="">Todos los ciclos</option>
        @for (op of opciones().ciclos; track op.id) { <option [value]="op.id">{{ op.nombre }}</option> }
      </select>
      <app-button type="submit" label="Filtrar" />
      <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm" (click)="bajar('pdf')">PDF</button>
      <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm" (click)="bajar('excel')">Excel</button>
    </form>
    @if (ind(); as indicadores) {
      <div class="mt-6 grid gap-3 sm:grid-cols-4">
        <app-stats-card title="Total" [number]="indicadores.total" />
        <app-stats-card title="Autoevaluación" [number]="indicadores.pct_auto + '%'" />
        <app-stats-card title="Firmadas" [number]="indicadores.pct_firmadas + '%'" />
        <app-stats-card title="Con observación" [number]="indicadores.pct_observacion + '%'" />
      </div>
    }
    <div class="mt-6">
      <app-dynamic-table [columns]="columnas" [rows]="filas()" />
    </div>
  `,
})
export class ReportesPage {
  private readonly http = inject(HttpClient);
  columnas = [
    { field: 'evaluado', header: 'Evaluado' },
    { field: 'ciclo', header: 'Ciclo' },
    { field: 'estado_display', header: 'Estado' },
    { field: 'area', header: 'Área' },
  ];
  filas = signal<Record<string, unknown>[]>([]);
  ind = signal<{ total: number; pct_auto: number; pct_firmadas: number; pct_observacion: number } | null>(null);
  opciones = signal<{ ciclos: { id: number; nombre: string }[] }>({ ciclos: [] });
  ciclo = '';

  constructor() {
    this.cargar();
  }

  valor(event: Event): string {
    return (event.target as HTMLSelectElement).value;
  }

  cargar(): void {
    const params: Record<string, string> = {};
    if (this.ciclo) {
      params['ciclo'] = this.ciclo;
    }
    this.http
      .get<{
        indicadores: { total: number; pct_auto: number; pct_firmadas: number; pct_observacion: number };
        evaluaciones: Record<string, unknown>[];
        opciones: { ciclos: { id: number; nombre: string }[] };
      }>(`${API}/reportes/iso/`, { params })
      .subscribe((data) => {
        this.ind.set(data.indicadores);
        this.filas.set(data.evaluaciones);
        this.opciones.set(data.opciones);
      });
  }

  bajar(formato: 'pdf' | 'excel'): void {
    const params: Record<string, string> = {};
    if (this.ciclo) {
      params['ciclo'] = this.ciclo;
    }
    this.http
      .get(`${API}/reportes/iso/${formato}/`, { params, responseType: 'blob' })
      .subscribe((blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = formato === 'pdf' ? 'reporte-iso.pdf' : 'reporte-iso.xlsx';
        enlace.click();
        URL.revokeObjectURL(url);
      });
  }
}

@Component({
  selector: 'app-auditoria',
  imports: [DynamicTableComponent],
  template: `
    <h1 class="text-2xl font-semibold">Auditoría</h1>
    <div class="mt-4">
      <app-dynamic-table [columns]="columnas" [rows]="filas()" />
    </div>
  `,
})
export class AuditoriaPage {
  private readonly http = inject(HttpClient);
  columnas = [
    { field: 'created_at', header: 'Fecha' },
    { field: 'usuario_email', header: 'Usuario' },
    { field: 'accion_display', header: 'Acción' },
    { field: 'modelo', header: 'Modelo' },
    { field: 'ip', header: 'IP' },
  ];
  filas = signal<Record<string, unknown>[]>([]);
  constructor() {
    this.http.get<{ pagina: Pagina<Record<string, unknown>> }>(`${API}/auditoria/`).subscribe((data) => {
      this.filas.set(data.pagina.results);
    });
  }
}

@Component({
  selector: 'app-ayuda',
  imports: [RouterLink],
  template: `
    <h1 class="text-2xl font-semibold">Ayuda</h1>
    @for (grupo of grupos(); track grupo.nombre) {
      <section class="mt-6">
        <h2 class="text-sm font-medium uppercase tracking-wide text-slate-500">{{ grupo.nombre }}</h2>
        <ul class="mt-2 space-y-2">
          @for (pagina of grupo.paginas; track pagina.slug) {
            <li>
              <a [routerLink]="['/ayuda', pagina.slug]" class="block rounded-xl border border-slate-200 bg-white px-4 py-3">
                <p class="font-medium">{{ pagina.titulo }}</p>
                <p class="text-sm text-slate-600">{{ pagina.resumen }}</p>
              </a>
            </li>
          }
        </ul>
      </section>
    }
  `,
})
export class AyudaPage {
  private readonly http = inject(HttpClient);
  grupos = signal<{ nombre: string; paginas: { slug: string; titulo: string; resumen: string }[] }[]>([]);
  constructor() {
    this.http
      .get<{ grupos: { nombre: string; paginas: { slug: string; titulo: string; resumen: string }[] }[] }>(
        `${API}/ayuda/`,
      )
      .subscribe((data) => this.grupos.set(data.grupos));
  }
}

@Component({
  selector: 'app-ayuda-pagina',
  imports: [RouterLink],
  template: `
    <a routerLink="/ayuda" class="text-sm text-sky-700">← Ayuda</a>
    @if (pagina(); as actual) {
      <h1 class="mt-3 text-2xl font-semibold">{{ actual.titulo }}</h1>
      <div class="mt-4 space-y-3 text-sm text-slate-700">
        @for (parrafo of actual.cuerpo; track parrafo) { <p>{{ parrafo }}</p> }
      </div>
    }
  `,
})
export class AyudaPaginaPage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  pagina = signal<{ titulo: string; cuerpo: string[] } | null>(null);
  constructor() {
    const slug = this.route.snapshot.paramMap.get('slug');
    this.http.get<{ titulo: string; cuerpo: string[] }>(`${API}/ayuda/${slug}/`).subscribe((data) => this.pagina.set(data));
  }
}

@Component({
  selector: 'app-vacio',
  template: `<p class="text-sm text-slate-500">No se encontró la página.</p>`,
})
export class VacioPage {
  readonly alertas = inject(AlertService);
}
