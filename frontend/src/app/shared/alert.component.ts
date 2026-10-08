import { Component, inject } from '@angular/core';

import { AlertService } from './alert.service';

@Component({
  selector: 'app-alert',
  template: `
    <div class="pointer-events-none fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
      @for (alerta of alertas.alertas(); track alerta.id) {
        <div
          class="pointer-events-auto rounded-xl px-3 py-2 text-sm shadow"
          [class]="alerta.tipo === 'success' ? 'bg-emerald-50 text-emerald-900' : 'bg-rose-50 text-rose-900'"
        >
          {{ alerta.texto }}
        </div>
      }
    </div>
  `,
})
export class AlertComponent {
  readonly alertas = inject(AlertService);
}
