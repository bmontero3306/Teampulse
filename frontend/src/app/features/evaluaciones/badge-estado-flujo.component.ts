import { Component, input } from '@angular/core';

const AMBAR =
  'inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200';
const VERDE =
  'inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200';
const ROJO =
  'inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800 ring-1 ring-inset ring-red-200';
const GRIS =
  'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200';

const ABIERTAS: Record<string, string> = {
  autoevaluacion: 'Autoevaluación',
  evaluacion_supervisor: 'Evaluación del supervisor',
  pendiente_reunion: 'Pendiente de reunión',
  pendiente_conformidad: 'Pendiente de conformidad',
};

@Component({
  selector: 'app-badge-estado-flujo',
  styles: [':host { display: contents; }'],
  template: `
    @if (estado() === 'cerrada' && conObservacion()) {
      <span [class]="rojo">{{ etiqueta() || 'Cerrada con observación' }}</span>
    } @else if (estado() === 'cerrada') {
      <span [class]="verde">{{ etiqueta() || 'Cerrada' }}</span>
    } @else if (abierta()) {
      <span [class]="ambar">{{ etiqueta() || abierta() }}</span>
    } @else if (estado() === 'cancelada' || estado() === 'cancelado') {
      <span [class]="rojo">Cancelada</span>
    } @else if (estado() === 'activa') {
      <span [class]="verde">Activa</span>
    } @else {
      <span [class]="gris">{{ etiqueta() || estado() }}</span>
    }
  `,
})
export class BadgeEstadoFlujoComponent {
  estado = input('');
  etiqueta = input('');
  conObservacion = input(false);
  readonly ambar = AMBAR;
  readonly verde = VERDE;
  readonly rojo = ROJO;
  readonly gris = GRIS;

  abierta(): string {
    return ABIERTAS[this.estado()] ?? '';
  }
}
