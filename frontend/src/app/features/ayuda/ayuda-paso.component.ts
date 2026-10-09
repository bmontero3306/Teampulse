import { Component, input } from '@angular/core';

import { AyudaBadgeComponent } from './ayuda-badge.component';

/** Paso de una guía. Copia app/templates/app/ayuda/_paso.html. */
@Component({
  selector: 'app-ayuda-paso',
  imports: [AyudaBadgeComponent],
  template: `
    <div class="relative pl-7">
      <span class="absolute left-0 top-1.5 h-3 w-3 rounded-full bg-sky-500 ring-4 ring-white"></span>
      @if (!ultimo()) {
        <span class="absolute left-[5px] top-5 bottom-0 w-px bg-slate-200"></span>
      }
      <div class="pb-6">
        <div class="flex flex-wrap items-center gap-2">
          @if (badge() === 'empresa') {
            <app-ayuda-badge tipo="empresa" [estado]="estado()" />
          } @else {
            <app-ayuda-badge [estado]="estado()" [contexto]="contexto()" [etiqueta]="titulo()" />
          }
          <span class="font-medium text-slate-900">{{ titulo() }}</span>
        </div>
        <p class="mt-1 text-slate-600">{{ texto() }}</p>
      </div>
    </div>
  `,
})
export class AyudaPasoComponent {
  estado = input.required<string>();
  contexto = input<'ciclo' | 'eval'>('eval');
  titulo = input.required<string>();
  texto = input.required<string>();
  badge = input('');
  ultimo = input(false);
}
