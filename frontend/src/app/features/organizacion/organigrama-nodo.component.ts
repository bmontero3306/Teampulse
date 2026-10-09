import { Component, computed, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

export interface NodoOrganigrama {
  id: number;
  nombre: string;
  area: string | null;
  descripcion: string;
  hijos: NodoOrganigrama[];
}

@Component({
  selector: 'app-nodo-org',
  imports: [NodoOrgComponent, RouterLink],
  template: `
    <li class="relative">
      <div
        [class]="
          tieneHijos()
            ? 'rounded-xl border border-slate-200 bg-white p-4 shadow-sm cursor-pointer'
            : 'rounded-xl border border-slate-200 bg-white p-4 shadow-sm'
        "
        [attr.data-org-card]="tieneHijos() ? '' : null"
        (click)="alClick($event)"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="flex min-w-0 items-start gap-3">
            @if (tieneHijos()) {
              <button
                type="button"
                class="org-toggle mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                [attr.aria-expanded]="abierto() ? 'true' : 'false'"
                [attr.aria-controls]="'org-hijos-' + nodo().id"
                [attr.data-org-nombre]="nodo().nombre"
                [attr.aria-label]="(abierto() ? 'Colapsar ' : 'Expandir ') + nodo().nombre"
              >
                <svg
                  class="h-4 w-4 transition-transform"
                  [class.rotate-90]="abierto()"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            }
            <div>
              <p class="font-semibold text-slate-900">{{ nodo().nombre }}</p>
              @if (nodo().area) {
                <p class="text-sm text-slate-500">{{ nodo().area }}</p>
              }
              @if (nodo().descripcion) {
                <p class="mt-1 text-sm text-slate-600">{{ nodo().descripcion }}</p>
              }
              @if (tieneHijos()) {
                <p class="mt-1 text-xs text-slate-500">
                  {{ nodo().hijos.length }} puesto{{ nodo().hijos.length === 1 ? '' : 's' }} a cargo
                </p>
              }
            </div>
          </div>
          @if (puedeEditar()) {
            <a
              [routerLink]="['/organizacion/puestos', nodo().id, 'editar']"
              class="text-sm font-medium text-sky-700 hover:text-sky-900"
              (click)="$event.stopPropagation()"
            >
              Editar
            </a>
          }
        </div>
      </div>
      @if (tieneHijos()) {
        <ul
          [id]="'org-hijos-' + nodo().id"
          class="org-hijos mt-3 space-y-3 border-l-2 border-sky-200 ml-4 pl-4"
          [class.hidden]="!abierto()"
          [attr.hidden]="abierto() ? null : ''"
        >
          @for (hijo of nodo().hijos; track hijo.id) {
            <app-nodo-org
              [nodo]="hijo"
              [abiertos]="abiertos()"
              [puedeEditar]="puedeEditar()"
              (alternar)="alternar.emit($event)"
            />
          }
        </ul>
      }
    </li>
  `,
})
export class NodoOrgComponent {
  nodo = input.required<NodoOrganigrama>();
  abiertos = input.required<ReadonlySet<number>>();
  puedeEditar = input(false);
  alternar = output<number>();

  readonly abierto = computed(() => this.abiertos().has(this.nodo().id));
  readonly tieneHijos = computed(() => this.nodo().hijos.length > 0);

  alClick(event: Event): void {
    if (!this.tieneHijos()) {
      return;
    }
    const objetivo = event.target;
    if (objetivo instanceof Element && objetivo.closest('a')) {
      return;
    }
    this.alternar.emit(this.nodo().id);
  }
}
