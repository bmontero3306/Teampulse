import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-button-icon',
  template: `
    <button
      type="button"
      [disabled]="disabled()"
      [attr.aria-label]="label()"
      [title]="label()"
      (click)="buttonClick.emit($event)"
      class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-50"
    >
      <i [attr.data-lucide]="icon()" class="h-4 w-4"></i>
    </button>
  `,
})
export class ButtonIconComponent {
  icon = input('circle');
  label = input('Acción');
  disabled = input(false);
  buttonClick = output<Event>();
}
