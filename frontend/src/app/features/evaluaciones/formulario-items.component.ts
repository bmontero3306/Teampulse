import { Component, computed, input } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { RespuestaFlujo, agruparItems, escalaDe, esTexto } from './flujo-modelos';

@Component({
  selector: 'app-formulario-items',
  imports: [FormsModule],
  styles: [':host { display: contents; }'],
  template: `
    @if (!grupos().length) {
      <p class="text-sm text-slate-500">Esta plantilla no tiene criterios.</p>
    } @else {
      <div class="space-y-4">
        @for (grupo of grupos(); track $index) {
          <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            @if (grupo.nombre) {
              <h2 class="border-b border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-800">
                {{ grupo.nombre }}
              </h2>
            }
            <table class="min-w-[520px] w-full text-left text-sm">
              <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
                <tr>
                  <th class="px-3 py-2 font-medium">Criterio</th>
                  <th class="px-3 py-2 font-medium w-24">Puntaje</th>
                  <th class="px-3 py-2 font-medium">
                    Devolución {{ rol() === 'empleado' ? 'del empleado' : 'del supervisor' }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 align-top">
                @for (item of grupo.items; track item.id) {
                  <tr>
                    <td class="px-3 py-2">
                      <p class="font-medium text-slate-900">{{ item.competencia }}</p>
                      @if (descripcion(item)) {
                        <p class="mt-0.5 text-xs text-slate-500">{{ descripcion(item) }}</p>
                      }
                      @if (esTexto(item)) {
                        <p class="mt-0.5 text-xs text-slate-400">Campo de texto</p>
                      } @else {
                        <p class="mt-0.5 text-xs text-slate-400">Escala {{ item.escala_min }}–{{ item.escala_max }}</p>
                      }
                    </td>
                    <td class="px-3 py-2 w-24">
                      @if (esTexto(item)) {
                        <span class="text-slate-400">—</span>
                      } @else if (rol() === 'empleado') {
                        <select
                          class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-20"
                          [name]="'puntaje-empleado-' + item.id"
                          [(ngModel)]="item.puntaje_empleado"
                          [disabled]="lectura()"
                        >
                          <option [ngValue]="null">—</option>
                          @for (n of escala(item); track n) {
                            <option [ngValue]="n">{{ n }}</option>
                          }
                        </select>
                      } @else {
                        <select
                          class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-20"
                          [name]="'puntaje-supervisor-' + item.id"
                          [(ngModel)]="item.puntaje_supervisor"
                          [disabled]="lectura()"
                        >
                          <option [ngValue]="null">—</option>
                          @for (n of escala(item); track n) {
                            <option [ngValue]="n">{{ n }}</option>
                          }
                        </select>
                      }
                    </td>
                    <td class="px-3 py-2 min-w-48">
                      @if (obligatoria(item)) {
                        <span class="mb-1 block text-xs font-medium text-slate-500">Obligatoria al enviar</span>
                      }
                      @if (rol() === 'empleado') {
                        <textarea
                          class="block w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-16"
                          rows="2"
                          [name]="'comentario-empleado-' + item.id"
                          [(ngModel)]="item.comentario_empleado"
                          [disabled]="lectura()"
                        ></textarea>
                      } @else {
                        <textarea
                          class="block w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 min-h-16"
                          rows="2"
                          [name]="'comentario-supervisor-' + item.id"
                          [(ngModel)]="item.comentario_supervisor"
                          [disabled]="lectura()"
                        ></textarea>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    }
  `,
})
export class FormularioItemsComponent {
  items = input.required<RespuestaFlujo[]>();
  rol = input.required<'empleado' | 'supervisor'>();
  lectura = input(false);
  descripciones = input<Record<string, string>>({});

  grupos = computed(() => agruparItems(this.items()));
  readonly esTexto = esTexto;
  readonly escala = escalaDe;

  obligatoria(item: RespuestaFlujo): boolean {
    return this.rol() === 'empleado'
      ? item.comentario_empleado_obligatorio
      : item.comentario_supervisor_obligatorio;
  }

  descripcion(item: RespuestaFlujo): string {
    return (this.descripciones()[item.competencia] || '').trim();
  }
}
