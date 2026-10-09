import { Component, input, output } from '@angular/core';

import {
  CHECKBOX_CSS,
  CompetenciaOpcion,
  CriterioEdicion,
  INPUT_CSS,
  textoDevolucion,
  textoTipoItem,
} from './evaluaciones-ui';

@Component({
  selector: 'tbody[appCriterioFila]',
  host: {
    class: 'fila-criterio border-b border-slate-100',
    '[class.is-abierto]': 'fila().abierto',
    '[class.opacity-50]': 'fila().quitar',
  },
  template: `
    <tr class="fila-resumen align-middle">
      <td class="py-3 pr-3 font-medium text-slate-900">
        <span class="js-resumen-competencia">{{ fila().competenciaNombre || '—' }}</span>
        @if (fila().errorGeneral) {
          <p class="mt-1 text-xs text-red-700">{{ fila().errorGeneral }}</p>
        }
      </td>
      <td class="py-3 pr-3 text-slate-600"><span class="js-resumen-categoria">{{ fila().categoria.trim() || '—' }}</span></td>
      <td class="py-3 pr-3 text-slate-600"><span class="js-resumen-tipo">{{ textoTipoItem(fila().tipo_item) }}</span></td>
      <td class="py-3 pr-3 text-slate-600"><span class="js-resumen-escala">{{ resumenEscala() }}</span></td>
      <td class="py-3 pr-3 text-slate-600"><span class="js-resumen-ponderacion">{{ resumenPonderacion() }}</span></td>
      <td class="py-3 pr-3 text-slate-600">
        <span class="js-resumen-devolucion">{{ textoDevolucion(fila().devEmpleado, fila().devSupervisor) }}</span>
      </td>
      <td class="py-3 text-right whitespace-nowrap">
        <div class="flex flex-col items-end gap-1">
          @if (fila().quitar) {
            <span class="js-aviso-quitar rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
              Se quitará al guardar
            </span>
          }
          <div>
            @if (!fila().quitar) {
              <button
                type="button"
                class="btn-editar-criterio rounded-lg px-2 py-1 text-sm font-medium text-sky-700 hover:bg-sky-50"
                (click)="editar.emit()"
              >
                {{ fila().abierto ? 'Cerrar' : 'Editar' }}
              </button>
              <button
                type="button"
                class="btn-quitar-criterio rounded-lg px-2 py-1 text-sm font-medium text-slate-600 hover:bg-slate-100"
                aria-label="Quitar de la plantilla"
                (click)="quitar.emit()"
              >
                Quitar
              </button>
            } @else {
              <button
                type="button"
                class="btn-deshacer-quitar rounded-lg px-2 py-1 text-sm font-medium text-sky-700 hover:bg-sky-50"
                (click)="deshacer.emit()"
              >
                Deshacer
              </button>
            }
          </div>
        </div>
      </td>
    </tr>
    <tr class="fila-detalle bg-slate-50" [class.hidden]="!fila().abierto">
      <td colspan="7" class="px-3 pb-4 pt-1">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div class="sm:col-span-2 lg:col-span-2">
            <label class="mb-1 block text-xs font-medium text-slate-700">Competencia</label>
            <select
              [class]="inputCss"
              [value]="fila().competencia ?? ''"
              (change)="cambiarCompetencia($event)"
            >
              <option value="">— Elegir competencia —</option>
              @for (comp of competencias(); track comp.id) {
                <option [value]="comp.id">{{ comp.nombre }}</option>
              }
            </select>
            @if (errores('competencia'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-700">Categoría</label>
            <input
              type="text"
              [class]="inputCss"
              list="categorias-plantilla"
              placeholder="Ej. Competencias generales"
              [value]="fila().categoria"
              (input)="patch({ categoria: valor($event) })"
            />
            @if (errores('categoria'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-700">Tipo de respuesta</label>
            <select [class]="inputCss + ' tipo-item'" [value]="fila().tipo_item" (change)="cambiarTipo($event)">
              <option value="escala">Escala numérica</option>
              <option value="texto">Solo texto</option>
            </select>
            @if (errores('tipo_item'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-700">Orden</label>
            <input
              type="number"
              min="1"
              [class]="inputCss"
              [value]="fila().orden"
              (input)="patch({ orden: valor($event) })"
            />
            @if (errores('orden'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="campo-escala" [class.opacity-40]="fila().tipo_item === 'texto'">
            <label class="mb-1 block text-xs font-medium text-slate-700">Escala mínima</label>
            <input type="number" [class]="inputCss" [value]="fila().escala_min" (input)="patch({ escala_min: valor($event) })" />
            @if (errores('escala_min'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="campo-escala" [class.opacity-40]="fila().tipo_item === 'texto'">
            <label class="mb-1 block text-xs font-medium text-slate-700">Escala máxima</label>
            <input type="number" [class]="inputCss" [value]="fila().escala_max" (input)="patch({ escala_max: valor($event) })" />
            @if (errores('escala_max'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="campo-escala" [class.opacity-40]="fila().tipo_item === 'texto'">
            <label class="mb-1 block text-xs font-medium text-slate-700">Ponderación (%)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              [class]="inputCss"
              [value]="fila().ponderacion"
              (input)="patch({ ponderacion: valor($event) })"
            />
            @if (errores('ponderacion'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
        </div>
        <p class="aviso-texto mt-3 text-xs text-slate-500" [class.hidden]="fila().tipo_item !== 'texto'">
          Solo texto: no lleva puntaje ni ponderación, y no suma al promedio.
        </p>
        <div class="mt-3 flex flex-col gap-2 sm:flex-row sm:gap-6">
          <label class="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              [class]="checkboxCss"
              [checked]="fila().devEmpleado"
              (change)="patch({ devEmpleado: marcado($event) })"
            />
            <span>
              <span class="font-medium">Devolución del empleado obligatoria</span>
              <span class="block text-xs text-slate-500">El evaluado debe dejar un comentario.</span>
            </span>
          </label>
          @if (errores('comentario_empleado_obligatorio'); as lista) {
            @if (lista.length) {
              <ul class="errorlist">
                @for (error of lista; track error) { <li>{{ error }}</li> }
              </ul>
            }
          }
          <label class="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              [class]="checkboxCss"
              [checked]="fila().devSupervisor"
              (change)="patch({ devSupervisor: marcado($event) })"
            />
            <span>
              <span class="font-medium">Devolución del supervisor obligatoria</span>
              <span class="block text-xs text-slate-500">El evaluador debe dejar feedback.</span>
            </span>
          </label>
          @if (errores('comentario_supervisor_obligatorio'); as lista) {
            @if (lista.length) {
              <ul class="errorlist">
                @for (error of lista; track error) { <li>{{ error }}</li> }
              </ul>
            }
          }
        </div>
      </td>
    </tr>
  `,
})
export class CriterioFilaComponent {
  readonly inputCss = INPUT_CSS;
  readonly checkboxCss = CHECKBOX_CSS;
  readonly textoDevolucion = textoDevolucion;
  readonly textoTipoItem = textoTipoItem;

  fila = input.required<CriterioEdicion>();
  competencias = input.required<CompetenciaOpcion[]>();
  cambio = output<CriterioEdicion>();
  editar = output<void>();
  quitar = output<void>();
  deshacer = output<void>();

  resumenEscala(): string {
    if (this.fila().tipo_item === 'texto') {
      return '—';
    }
    const min = this.fila().escala_min;
    const max = this.fila().escala_max;
    return min && max ? `${min}–${max}` : '—';
  }

  resumenPonderacion(): string {
    if (this.fila().tipo_item === 'texto') {
      return '—';
    }
    const pond = this.fila().ponderacion;
    return pond === '' ? '—' : `${pond}%`;
  }

  errores(campo: string): string[] {
    return this.fila().errores[campo] ?? [];
  }

  patch(parcial: Partial<CriterioEdicion>): void {
    const siguiente: CriterioEdicion = { ...this.fila(), ...parcial };
    if (parcial.tipo_item === 'texto') {
      siguiente.ponderacion = '0';
    }
    this.cambio.emit(siguiente);
  }

  cambiarCompetencia(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    const id = value ? Number(value) : null;
    const comp = this.competencias().find((item) => item.id === id);
    this.patch({ competencia: id, competenciaNombre: comp?.nombre ?? '' });
  }

  cambiarTipo(event: Event): void {
    const value = (event.target as HTMLSelectElement).value === 'texto' ? 'texto' : 'escala';
    this.patch({ tipo_item: value });
  }

  valor(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  marcado(event: Event): boolean {
    return (event.target as HTMLInputElement).checked;
  }
}
