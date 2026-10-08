import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-modal',
  template: `
    @if (open()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" (click)="cancel.emit()">
        <div class="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl" (click)="$event.stopPropagation()">
          <h2 class="text-lg font-semibold text-slate-900">{{ title() }}</h2>
          <div class="mt-3 text-sm text-slate-600">
            <ng-content />
          </div>
          <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100" (click)="cancel.emit()">
              Cancelar
            </button>
            <button type="button" class="rounded-lg bg-sky-700 px-3 py-2 text-sm text-white" (click)="confirm.emit()">
              Confirmar
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ModalComponent {
  open = input(false);
  title = input('');
  confirm = output<void>();
  cancel = output<void>();
}
