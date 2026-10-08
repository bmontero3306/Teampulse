import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-button',
  template: `
    <button
      [type]="type()"
      [disabled]="disabled()"
      (click)="buttonClick.emit($event)"
      [class]="clases()"
    >
      {{ label() }}
    </button>
  `,
})
export class ButtonComponent {
  label = input('Aceptar');
  color = input<'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'light' | 'dark' | 'link'>(
    'primary',
  );
  size = input<'sm' | 'md' | 'lg'>('md');
  disabled = input(false);
  type = input<'button' | 'submit'>('button');
  buttonClick = output<Event>();

  clases(): string {
    const base = 'inline-flex items-center justify-center rounded-lg font-medium disabled:opacity-50';
    const size = this.size() === 'sm' ? 'px-2.5 py-1.5 text-xs' : this.size() === 'lg' ? 'px-4 py-2.5 text-base' : 'px-3 py-2 text-sm';
    const colores: Record<string, string> = {
      primary: 'bg-sky-700 text-white hover:bg-sky-800',
      secondary: 'bg-slate-200 text-slate-800 hover:bg-slate-300',
      success: 'bg-emerald-600 text-white hover:bg-emerald-700',
      danger: 'bg-rose-600 text-white hover:bg-rose-700',
      warning: 'bg-amber-500 text-white hover:bg-amber-600',
      info: 'bg-cyan-600 text-white hover:bg-cyan-700',
      light: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50',
      dark: 'bg-slate-800 text-white hover:bg-slate-900',
      link: 'bg-transparent text-sky-700 hover:underline px-0',
    };
    return `${base} ${size} ${colores[this.color()]}`;
  }
}
