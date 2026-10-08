import { Component, input, output } from '@angular/core';

import { Columna } from '../core/models';

@Component({
  selector: 'app-dynamic-table',
  template: `
    <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            @for (col of columns(); track col.field) {
              <th class="px-3 py-2 font-medium">{{ col.header }}</th>
            }
            @if (showOptions()) {
              <th class="px-3 py-2 font-medium">Acciones</th>
            }
          </tr>
        </thead>
        <tbody>
          @for (row of rows(); track $index) {
            <tr class="border-b border-slate-100 last:border-0">
              @for (col of columns(); track col.field) {
                <td class="px-3 py-2 text-slate-700">{{ valor(row, col.field) }}</td>
              }
              @if (showOptions()) {
                <td class="px-3 py-2">
                  <button type="button" class="text-sky-700 hover:underline" (click)="rowClick.emit(row)">
                    Abrir
                  </button>
                </td>
              }
            </tr>
          } @empty {
            <tr>
              <td class="px-3 py-6 text-slate-500" [attr.colspan]="columns().length + (showOptions() ? 1 : 0)">
                No hay registros.
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class DynamicTableComponent {
  columns = input<Columna[]>([]);
  rows = input<Record<string, unknown>[]>([]);
  showOptions = input(false);
  rowClick = output<Record<string, unknown>>();

  valor(row: Record<string, unknown>, field: string): unknown {
    return field.split('.').reduce<unknown>((acc, key) => {
      if (acc && typeof acc === 'object') {
        return (acc as Record<string, unknown>)[key];
      }
      return '';
    }, row);
  }
}
