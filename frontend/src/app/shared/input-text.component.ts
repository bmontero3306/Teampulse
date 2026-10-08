import { Component, input } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-input-text',
  imports: [ReactiveFormsModule],
  template: `
    <label class="block text-sm">
      <span class="font-medium text-slate-700">
        {{ label() }}
        @if (required()) { <span class="text-rose-600">*</span> }
      </span>
      <input
        [type]="type()"
        [formControl]="control()"
        [placeholder]="placeholder()"
        [attr.maxlength]="maxlength()"
        [attr.autocomplete]="autocomplete()"
        class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
      />
      @if (help()) { <span class="mt-1 block text-xs text-slate-500">{{ help() }}</span> }
      @if (control().touched && control().invalid) {
        <span class="mt-1 block text-xs text-rose-600">{{ error() }}</span>
      }
    </label>
  `,
})
export class InputTextComponent {
  label = input('');
  placeholder = input('');
  required = input(false);
  help = input('');
  type = input('text');
  autocomplete = input('');
  maxlength = input<number | null>(null);
  control = input.required<FormControl>();

  error(): string {
    const errores = this.control().errors ?? {};
    if (errores['required']) return 'Este campo es obligatorio.';
    if (errores['email']) return 'Ingresá un correo válido.';
    if (errores['minlength']) return `Mínimo ${errores['minlength'].requiredLength} caracteres.`;
    if (errores['maxlength']) return `Máximo ${errores['maxlength'].requiredLength} caracteres.`;
    return 'El valor no es válido.';
  }
}
