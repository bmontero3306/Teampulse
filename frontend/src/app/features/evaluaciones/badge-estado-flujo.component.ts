import { Component, input } from '@angular/core';

@Component({
  selector: 'app-badge-estado-flujo',
  styles: [':host { display: contents; }'],
  template: `
    @if (estado() === 'cerrada') {
      <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">Cerrada</span>
    } @else if (estado() === 'cerrada_con_obs') {
      <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cerrada con observación</span>
    } @else if (estado() === 'pendiente_auto') {
      <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de autoevaluación</span>
    } @else if (estado() === 'pendiente_comparacion') {
      <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de comparación</span>
    } @else if (estado() === 'pendiente_conformidad') {
      <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">Pendiente de conformidad</span>
    } @else if (estado() === 'pausado' || estado() === 'auto_borrador' || estado() === 'auto_completa' || estado() === 'supervisor_borrador') {
      <span class="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">{{ etiqueta() || estado() }}</span>
    } @else if (estado() === 'cancelada' || estado() === 'cancelado') {
      <span class="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200">Cancelada</span>
    } @else if (estado() === 'activa') {
      <span class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">Activa</span>
    } @else {
      <span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">{{ etiqueta() || estado() }}</span>
    }
  `,
})
export class BadgeEstadoFlujoComponent {
  estado = input('');
  etiqueta = input('');
}
