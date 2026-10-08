import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { BadgeComponent } from '../../shared/badge.component';
import { StatsCardComponent } from '../../shared/stats-card.component';

interface Dashboard {
  ciclo_activo: { id: number; nombre: string; fecha_cierre: string } | null;
  kpis: { participantes: number; auto: number; supervisor: number; firmadas: number; sin_evaluador: number } | null;
  pendientes: { evaluacion_id: number; accion: string; href: string; ciclo: string }[];
  accesos_rapidos: { clave: string; etiqueta: string; href: string }[];
  equipo: {
    total: number;
    completitud: number;
    alertas_sin_auto: { id: number; evaluado: string }[];
    evaluaciones: { id: number; evaluado: string; estado_display: string }[];
  } | null;
  empresas_plataforma: { id: number; nombre: string; estado: string }[];
  mostrar_pendientes: boolean;
  mostrar_equipo: boolean;
  mostrar_kpis: boolean;
  mostrar_empresas: boolean;
}

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, StatsCardComponent, BadgeComponent],
  template: `
    <h1 class="text-2xl font-semibold">Panel</h1>
    @if (data(); as panel) {
      @if (panel.ciclo_activo) {
        <p class="mt-2 text-sm text-slate-600">
          Ciclo activo: {{ panel.ciclo_activo.nombre }} · cierra {{ panel.ciclo_activo.fecha_cierre }}
        </p>
      }
      @if (panel.mostrar_kpis && panel.kpis) {
        <div class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <app-stats-card title="Participantes" [number]="panel.kpis.participantes" />
          <app-stats-card title="Autoevaluaciones" [number]="panel.kpis.auto" />
          <app-stats-card title="Supervisor" [number]="panel.kpis.supervisor" />
          <app-stats-card title="Firmadas" [number]="panel.kpis.firmadas" />
          <app-stats-card title="Sin evaluador" [number]="panel.kpis.sin_evaluador" />
        </div>
      }
      @if (panel.mostrar_empresas) {
        <section class="mt-8">
          <h2 class="text-lg font-semibold">Empresas</h2>
          <ul class="mt-3 divide-y rounded-xl border border-slate-200 bg-white">
            @for (empresa of panel.empresas_plataforma; track empresa.id) {
              <li class="flex items-center justify-between px-4 py-3 text-sm">
                <span>{{ empresa.nombre }}</span>
                <app-badge [label]="empresa.estado" [tono]="empresa.estado === 'activa' ? 'ok' : 'warn'" />
              </li>
            }
          </ul>
        </section>
      }
      @if (panel.mostrar_pendientes) {
        <section class="mt-8">
          <h2 class="text-lg font-semibold">Pendientes</h2>
          <ul class="mt-3 space-y-2">
            @for (item of panel.pendientes; track item.evaluacion_id) {
              <li>
                <a [routerLink]="item.href" class="block rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm hover:border-sky-300">
                  <span class="font-medium">{{ item.accion }}</span>
                  <span class="text-slate-500"> · {{ item.ciclo }}</span>
                </a>
              </li>
            } @empty {
              <li class="text-sm text-slate-500">No tenés pendientes en el ciclo activo.</li>
            }
          </ul>
          <div class="mt-4 flex gap-3">
            @for (acceso of panel.accesos_rapidos; track acceso.clave) {
              <a [routerLink]="acceso.href" class="text-sm text-sky-700">{{ acceso.etiqueta }}</a>
            }
          </div>
        </section>
      }
      @if (panel.mostrar_equipo && panel.equipo) {
        <section class="mt-8">
          <h2 class="text-lg font-semibold">Equipo · {{ panel.equipo.completitud }}% con autoevaluación</h2>
          <ul class="mt-3 divide-y rounded-xl border border-slate-200 bg-white">
            @for (ev of panel.equipo.evaluaciones; track ev.id) {
              <li class="flex justify-between px-4 py-3 text-sm">
                <a [routerLink]="['/evaluaciones', ev.id, 'supervisar']" class="text-sky-800">{{ ev.evaluado }}</a>
                <span class="text-slate-500">{{ ev.estado_display }}</span>
              </li>
            }
          </ul>
        </section>
      }
    }
  `,
})
export class DashboardPage {
  private readonly http = inject(HttpClient);
  data = signal<Dashboard | null>(null);

  constructor() {
    this.http.get<Dashboard>(`${API}/dashboard/`).subscribe((panel) => this.data.set(panel));
  }
}
