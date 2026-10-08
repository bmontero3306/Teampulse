import { Component, input } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-input-number',
  imports: [ReactiveFormsModule],
  template: `
    <label class="block text-sm">
      <span class="font-medium text-slate-700">{{ label() }}</span>
      <input
        type="number"
        [formControl]="control()"
        [attr.min]="min()"
        [attr.max]="max()"
        class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-sky-500"
      />
    </label>
  `,
})
export class InputNumberComponent {
  label = input('');
  min = input<number | null>(null);
  max = input<number | null>(null);
  control = input.required<FormControl>();
}
