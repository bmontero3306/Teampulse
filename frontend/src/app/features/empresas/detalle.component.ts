import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EmpresaBadgeEstadoComponent } from './badge-estado.component';
import { Empresa, formatearCuit } from './empresa.model';

@Component({
  selector: 'app-empresa-detalle',
  imports: [RouterLink, EmpresaBadgeEstadoComponent],
  template: `
    <section class="mx-auto max-w-3xl">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          @if (rol() === 'superadmin') {
            <p class="text-sm font-medium text-sky-700">
              <a routerLink="/empresas" class="hover:text-sky-800">Empresas</a>
            </p>
          }
          <h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{{ empresa().nombre }}</h1>
          <div class="mt-2"><app-empresa-badge [estado]="empresa().estado" /></div>
        </div>
        <div class="flex flex-wrap gap-2">
          <a
            [routerLink]="['/empresas', empresa().id, 'editar']"
            class="inline-flex items-center justify-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-700"
          >
            Editar
          </a>
          @if (rol() === 'superadmin') {
            @if (empresa().estado !== 'suspendida') {
              <a
                [routerLink]="['/empresas', empresa().id, 'suspender']"
                class="inline-flex items-center justify-center rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              >
                Suspender
              </a>
            }
            @if (empresa().estado !== 'activa') {
              <form (submit)="$event.preventDefault(); activar.emit(empresa())">
                <button
                  type="submit"
                  class="inline-flex items-center justify-center rounded-lg border border-emerald-200 bg-white px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"
                >
                  Activar
                </button>
              </form>
            }
          }
        </div>
      </div>

      <dl class="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Razón social</dt>
          <dd class="mt-1 text-slate-900">{{ empresa().razon_social }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">CUIT</dt>
          <dd class="mt-1 text-slate-900">{{ cuit(empresa().cuit) }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Email de contacto</dt>
          <dd class="mt-1 text-slate-900">{{ empresa().email_contacto }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Teléfono</dt>
          <dd class="mt-1 text-slate-900">{{ empresa().telefono || '—' }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:col-span-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Dirección</dt>
          <dd class="mt-1 text-slate-900">{{ empresa().direccion || '—' }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Usuarios</dt>
          <dd class="mt-1 text-slate-900">{{ usuarios(empresa()) }}</dd>
        </div>
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <dt class="text-xs font-medium uppercase tracking-wide text-slate-500">Estado</dt>
          <dd class="mt-1"><app-empresa-badge [estado]="empresa().estado" /></dd>
        </div>
      </dl>
    </section>
  `,
})
export class EmpresaDetalleComponent {
  empresa = input.required<Empresa>();
  rol = input('');
  activar = output<Empresa>();

  cuit(valor: string): string {
    return formatearCuit(valor);
  }

  usuarios(empresa: Empresa): string | number {
    return empresa.cantidad_usuarios ?? '—';
  }
}
