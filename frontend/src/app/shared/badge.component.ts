import { Component, input } from '@angular/core';

@Component({
  selector: 'app-badge',
  template: `<span [class]="clases()">{{ label() }}</span>`,
})
export class BadgeComponent {
  label = input('');
  tono = input<'neutral' | 'ok' | 'warn' | 'info'>('neutral');

  clases(): string {
    const base = 'inline-flex rounded-full px-2 py-0.5 text-xs font-medium';
    const tonos = {
      neutral: 'bg-slate-100 text-slate-700',
      ok: 'bg-emerald-50 text-emerald-800',
      warn: 'bg-amber-50 text-amber-800',
      info: 'bg-sky-50 text-sky-800',
    };
    return `${base} ${tonos[this.tono()]}`;
  }
}
