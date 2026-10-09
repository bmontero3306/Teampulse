import { Component, input, linkedSignal, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ESTADOS_EMPRESA, Empresa, formatearCuit } from './empresa.model';
import { EmpresaBadgeEstadoComponent } from './badge-estado.component';

@Component({
  selector: 'app-empresa-lista',
  imports: [RouterLink, EmpresaBadgeEstadoComponent],
  template: `
    <section>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Empresas</h1>
          <p class="mt-1 text-sm text-slate-600">Gestión de empresas de la plataforma.</p>
        </div>
        <a
          routerLink="/empresas/nueva"
          class="inline-flex items-center justify-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-700"
        >
          Nueva empresa
        </a>
      </div>

      <form class="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end" (submit)="$event.preventDefault(); filtrar.emit(filtroLocal())">
        <div class="sm:w-56">
          <label for="filtro-estado" class="mb-1 block text-sm font-medium text-slate-700">Estado</label>
          <select
            id="filtro-estado"
            name="estado"
            (change)="elegirFiltro($event)"
            class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="" [selected]="filtroLocal() === ''">Todos</option>
            @for (opcion of estados; track opcion.value) {
              <option [value]="opcion.value" [selected]="filtroLocal() === opcion.value">{{ opcion.label }}</option>
            }
          </select>
        </div>
        <button
          type="submit"
          class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Filtrar
        </button>
        @if (estadoFiltro()) {
          <a
            routerLink="/empresas"
            class="inline-flex items-center justify-center px-2 py-2 text-sm font-medium text-sky-700 hover:text-sky-800"
          >
            Quitar filtro
          </a>
        }
      </form>

      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-700">Nombre</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-700">CUIT</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-700">Estado</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-700">Usuarios</th>
              <th scope="col" class="px-4 py-3 text-right font-semibold text-slate-700">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (empresa of empresas(); track empresa.id) {
              <tr class="hover:bg-slate-50">
                <td class="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                  <a
                    [routerLink]="['/empresas', empresa.id]"
                    class="hover:text-sky-700"
                    >{{ empresa.nombre }}</a
                  >
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ cuit(empresa.cuit) }}</td>
                <td class="whitespace-nowrap px-4 py-3">
                  <app-empresa-badge [estado]="empresa.estado" />
                </td>
                <td class="whitespace-nowrap px-4 py-3 text-slate-600">{{ usuarios(empresa) }}</td>
                <td class="whitespace-nowrap px-4 py-3 text-right">
                  <div class="flex flex-wrap justify-end gap-2">
                    <a
                      [routerLink]="['/empresas', empresa.id]"
                      class="font-medium text-sky-700 hover:text-sky-800"
                      >Ver</a
                    >
                    <a
                      [routerLink]="['/empresas', empresa.id, 'editar']"
                      class="font-medium text-slate-700 hover:text-slate-900"
                      >Editar</a
                    >
                    @if (empresa.estado !== 'suspendida') {
                      <a
                        [routerLink]="['/empresas', empresa.id, 'suspender']"
                        class="font-medium text-red-700 hover:text-red-800"
                        >Suspender</a
                      >
                    }
                    @if (empresa.estado !== 'activa') {
                      <form class="inline" (submit)="$event.preventDefault(); activar.emit(empresa)">
                        <button type="submit" class="font-medium text-emerald-700 hover:text-emerald-800">Activar</button>
                      </form>
                    }
                    <form class="inline" (submit)="$event.preventDefault(); usar.emit(empresa)">
                      <button type="submit" class="font-medium text-slate-500 hover:text-slate-800">Usar</button>
                    </form>
                  </div>
                </td>
              </tr>
            } @empty {
              @if (!cargando()) {
                <tr>
                  <td colspan="5" class="px-4 py-10 text-center text-slate-500">
                    No hay empresas{{ estadoFiltro() ? ' con ese estado' : '' }}.
                    <a
                      routerLink="/empresas/nueva"
                      class="font-medium text-sky-700 hover:text-sky-800"
                      >Crear la primera</a
                    >
                  </td>
                </tr>
              }
            }
          </tbody>
        </table>
      </div>
    </section>
  `,
})
export class EmpresaListaComponent {
  readonly estados = ESTADOS_EMPRESA;
  empresas = input<Empresa[]>([]);
  estadoFiltro = input('');
  cargando = input(false);
  filtrar = output<string>();
  activar = output<Empresa>();
  usar = output<Empresa>();
  filtroLocal = linkedSignal(() => this.estadoFiltro());

  elegirFiltro(event: Event): void {
    this.filtroLocal.set((event.target as HTMLSelectElement).value);
  }

  cuit(valor: string): string {
    return formatearCuit(valor);
  }

  usuarios(empresa: Empresa): string | number {
    return empresa.cantidad_usuarios ?? '—';
  }
}
