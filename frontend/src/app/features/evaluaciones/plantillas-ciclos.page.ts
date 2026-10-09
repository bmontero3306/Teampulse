import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import { BadgeEstadoComponent } from './badge-estado.component';
import { BadgeTipoComponent } from './badge-tipo.component';
import {
  CicloApi,
  PlantillaApi,
  esGestion,
  fechaCorta,
  listarTodo,
} from './evaluaciones-ui';

@Component({
  selector: 'app-plantillas',
  imports: [BadgeTipoComponent, RouterLink],
  template: `
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Plantillas de evaluación</h1>
        <p class="mt-1 text-sm text-slate-600">Criterios, escalas y puestos asociados a cada plantilla.</p>
      </div>
      @if (puedeEditar()) {
        <a
          routerLink="/evaluaciones/plantillas/nueva"
          class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          Nueva plantilla
        </a>
      }
    </div>

    <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
          <tr>
            <th class="px-4 py-3 font-medium">Nombre</th>
            <th class="px-4 py-3 font-medium">Tipo</th>
            <th class="px-4 py-3 font-medium">Puestos asociados</th>
            <th class="px-4 py-3 font-medium">Estado</th>
            @if (puedeEditar()) {
              <th class="px-4 py-3 font-medium"></th>
            }
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          @for (plantilla of plantillas(); track plantilla.id) {
            <tr>
              <td class="px-4 py-3 font-medium text-slate-900">{{ plantilla.nombre }}</td>
              <td class="px-4 py-3">
                <app-badge-tipo [tipo]="plantilla.tipo" />
              </td>
              <td class="px-4 py-3 text-slate-600">
                @for (puesto of plantilla.puestos_nombres ?? []; track $index) {
                  <span class="mr-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{{ puesto }}</span>
                } @empty {
                  <span class="text-slate-400">—</span>
                }
              </td>
              <td class="px-4 py-3">
                @if (plantilla.activa) {
                  <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">Activa</span>
                } @else {
                  <span class="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Inactiva</span>
                }
              </td>
              @if (puedeEditar()) {
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <a [routerLink]="['/evaluaciones/plantillas', plantilla.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-900">
                    Editar
                  </a>
                  <button type="button" class="ml-3 font-medium text-slate-600 hover:text-slate-900" (click)="duplicar(plantilla)">
                    Duplicar
                  </button>
                </td>
              }
            </tr>
          } @empty {
            <tr>
              <td colspan="5" class="px-4 py-8 text-center text-slate-500">No hay plantillas para mostrar.</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class PlantillasPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly title = inject(Title);

  plantillas = signal<PlantillaApi[]>([]);
  puedeEditar = computed(() => esGestion(this.auth.sesion()?.usuario.rol));

  constructor() {
    this.title.setTitle('Plantillas · TeamPulse');
    this.cargar();
  }

  cargar(): void {
    listarTodo<PlantillaApi>(this.http, `${API}/plantillas/`).subscribe({
      next: (lista) => this.plantillas.set(lista),
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  duplicar(plantilla: PlantillaApi): void {
    this.http.post<PlantillaApi>(`${API}/plantillas/${plantilla.id}/duplicar/`, {}).subscribe({
      next: (copia) => {
        this.alertas.success(`Se creó la plantilla «${copia.nombre}».`);
        void this.router.navigate(['/evaluaciones/plantillas', copia.id, 'editar']);
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}

@Component({
  selector: 'app-ciclos',
  imports: [RouterLink, BadgeEstadoComponent],
  template: `
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Ciclos de evaluación</h1>
        <p class="mt-1 text-sm text-slate-600">Alta, activación y seguimiento de ciclos por empresa.</p>
      </div>
      @if (puedeGestionar()) {
        <a
          routerLink="/evaluaciones/ciclos/nuevo"
          class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          Nuevo ciclo
        </a>
      }
    </div>

    <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
          <tr>
            <th class="px-4 py-3 font-medium">Nombre</th>
            <th class="px-4 py-3 font-medium">Estado</th>
            <th class="px-4 py-3 font-medium">Inicio</th>
            <th class="px-4 py-3 font-medium">Cierre</th>
            <th class="px-4 py-3 font-medium">Plantilla</th>
            <th class="px-4 py-3 font-medium">Participantes</th>
            <th class="px-4 py-3 font-medium"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          @for (ciclo of ciclos(); track ciclo.id) {
            <tr>
              <td class="px-4 py-3 font-medium text-slate-900">
                <a [routerLink]="['/evaluaciones/ciclos', ciclo.id]" class="hover:text-sky-700">{{ ciclo.nombre }}</a>
              </td>
              <td class="px-4 py-3">
                <app-badge-estado [estado]="ciclo.estado" contexto="ciclo" />
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-slate-600">{{ fecha(ciclo.fecha_inicio) }}</td>
              <td class="px-4 py-3 whitespace-nowrap text-slate-600">{{ fecha(ciclo.fecha_cierre) }}</td>
              <td class="px-4 py-3 text-slate-600">{{ ciclo.plantilla_nombre }}</td>
              <td class="px-4 py-3 text-slate-600">{{ ciclo.total_evals ?? 0 }}</td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <a [routerLink]="['/evaluaciones/ciclos', ciclo.id]" class="font-medium text-sky-700 hover:text-sky-900">Ver</a>
              </td>
            </tr>
          } @empty {
            <tr>
              <td colspan="7" class="px-4 py-8 text-center text-slate-500">No hay ciclos para mostrar.</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class CiclosPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  private readonly title = inject(Title);

  readonly fecha = fechaCorta;
  ciclos = signal<CicloApi[]>([]);
  puedeGestionar = computed(() => esGestion(this.auth.sesion()?.usuario.rol));

  constructor() {
    this.title.setTitle('Ciclos · TeamPulse');
    this.cargar();
  }

  cargar(): void {
    listarTodo<CicloApi>(this.http, `${API}/ciclos/`).subscribe({
      next: (lista) => this.ciclos.set(lista),
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}
