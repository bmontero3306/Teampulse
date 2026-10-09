import { Component, input } from '@angular/core';

@Component({
  selector: 'app-badge-estado',
  template: `
    @if (contexto() === 'ciclo') {
      @switch (estado()) {
        @case ('activo') {
          <span class="inline-flex items-center rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-medium text-sky-800 ring-1 ring-inset ring-sky-200">Activo</span>
        }
        @case ('pausado') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pausado</span>
        }
        @case ('cancelado') {
          <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cancelado</span>
        }
        @case ('cerrado') {
          <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">Cerrado</span>
        }
        @case ('borrador') {
          <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">Borrador</span>
        }
        @default {
          <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">{{ etiqueta() || estado() }}</span>
        }
      }
    } @else {
      @switch (estado()) {
        @case ('cerrada') {
          <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">Cerrada</span>
        }
        @case ('cerrada_con_obs') {
          <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cerrada con observación</span>
        }
        @case ('pendiente_auto') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de autoevaluación</span>
        }
        @case ('pendiente_comparacion') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de comparación</span>
        }
        @case ('pendiente_conformidad') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de conformidad</span>
        }
        @case ('pausado') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">{{ etiqueta() || estado() }}</span>
        }
        @case ('auto_borrador') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">{{ etiqueta() || estado() }}</span>
        }
        @case ('auto_completa') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">{{ etiqueta() || estado() }}</span>
        }
        @case ('supervisor_borrador') {
          <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">{{ etiqueta() || estado() }}</span>
        }
        @case ('cancelada') {
          <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cancelada</span>
        }
        @case ('cancelado') {
          <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cancelada</span>
        }
        @case ('activa') {
          <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">Activa</span>
        }
        @default {
          <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">{{ etiqueta() || estado() }}</span>
        }
      }
    }
  `,
})
export class BadgeEstadoComponent {
  estado = input('');
  contexto = input<'ciclo' | 'evaluacion'>('ciclo');
  etiqueta = input('');
}
