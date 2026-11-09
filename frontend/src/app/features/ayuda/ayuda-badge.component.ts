import { Component, computed, input } from '@angular/core';

const BASE =
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset';

type Tono = 'sky' | 'amber' | 'red' | 'emerald' | 'slate';

function tono(color: Tono): string {
  const colores: Record<Tono, string> = {
    sky: 'bg-sky-50 text-sky-800 ring-sky-200',
    amber: 'bg-amber-50 text-amber-800 ring-amber-200',
    red: 'bg-red-50 text-red-800 ring-red-200',
    emerald: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    slate: 'bg-slate-100 text-slate-700 ring-slate-200',
  };
  return `${BASE} ${colores[color]}`;
}

export interface BadgeVista {
  texto: string;
  clase: string;
}

/** Clases y etiquetas de evaluaciones/_badge_estado.html y empresas/_badge_estado.html. */
export function resolverBadge(
  tipo: 'estado' | 'empresa',
  contexto: 'ciclo' | 'eval',
  estado: string,
  etiqueta: string | null,
): BadgeVista {
  if (tipo === 'empresa') {
    if (estado === 'activa') return { texto: 'Activa', clase: tono('emerald') };
    if (estado === 'suspendida') return { texto: 'Suspendida', clase: tono('red') };
    if (estado === 'inactiva') return { texto: 'Inactiva', clase: tono('slate') };
    return { texto: estado, clase: tono('slate') };
  }

  if (contexto === 'ciclo') {
    if (estado === 'activo') return { texto: 'Activo', clase: tono('sky') };
    if (estado === 'pausado') return { texto: 'Pausado', clase: tono('amber') };
    if (estado === 'cancelado') return { texto: 'Cancelado', clase: tono('red') };
    if (estado === 'cerrado') return { texto: 'Cerrado', clase: tono('emerald') };
    if (estado === 'borrador') return { texto: 'Borrador', clase: tono('slate') };
    return { texto: etiqueta || estado, clase: tono('slate') };
  }

  if (estado === 'cerrada' && etiqueta === 'Cerrada con observación') {
    return { texto: etiqueta, clase: tono('red') };
  }
  if (estado === 'cerrada') return { texto: etiqueta || 'Cerrada', clase: tono('emerald') };
  if (estado === 'autoevaluacion') return { texto: etiqueta || 'Autoevaluación', clase: tono('amber') };
  if (estado === 'evaluacion_supervisor') {
    return { texto: etiqueta || 'Evaluación del supervisor', clase: tono('amber') };
  }
  if (estado === 'pendiente_reunion') return { texto: etiqueta || 'Pendiente de reunión', clase: tono('amber') };
  if (estado === 'pendiente_conformidad') return { texto: 'Pendiente de conformidad', clase: tono('amber') };
  if (estado === 'pausado') return { texto: etiqueta || estado, clase: tono('amber') };
  if (estado === 'cancelada' || estado === 'cancelado') return { texto: 'Cancelada', clase: tono('red') };
  if (estado === 'activa') return { texto: 'Activa', clase: tono('emerald') };
  return { texto: etiqueta || estado, clase: tono('slate') };
}

@Component({
  selector: 'app-ayuda-badge',
  template: `<span [class]="vista().clase">{{ vista().texto }}</span>`,
})
export class AyudaBadgeComponent {
  estado = input.required<string>();
  contexto = input<'ciclo' | 'eval'>('eval');
  etiqueta = input<string | null>(null);
  tipo = input<'estado' | 'empresa'>('estado');

  readonly vista = computed(() =>
    resolverBadge(this.tipo(), this.contexto(), this.estado(), this.etiqueta()),
  );
}
