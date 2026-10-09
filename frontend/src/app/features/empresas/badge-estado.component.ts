import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empresa-badge',
  template: `
    @switch (estado()) {
      @case ('activa') {
        <span
          class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200"
          >Activa</span
        >
      }
      @case ('suspendida') {
        <span
          class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200"
          >Suspendida</span
        >
      }
      @case ('inactiva') {
        <span
          class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200"
          >Inactiva</span
        >
      }
      @default {
        <span
          class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200"
          >{{ estado() }}</span
        >
      }
    }
  `,
})
export class EmpresaBadgeEstadoComponent {
  estado = input('');
}
