import { Component, input } from '@angular/core';

@Component({
  selector: 'app-badge-tipo',
  template: `
    @switch (tipo()) {
      @case ('tecnica') {
        <span class="inline-flex items-center rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-medium text-sky-800 ring-1 ring-inset ring-sky-200">Técnica</span>
      }
      @case ('actitudinal') {
        <span class="inline-flex items-center rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-800 ring-1 ring-inset ring-violet-200">Actitudinal</span>
      }
      @case ('objetivos') {
        <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Objetivos</span>
      }
      @case ('mixta') {
        <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800 ring-1 ring-inset ring-slate-200">Mixta</span>
      }
      @default {
        <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">{{ tipo() }}</span>
      }
    }
  `,
})
export class BadgeTipoComponent {
  tipo = input('');
}
