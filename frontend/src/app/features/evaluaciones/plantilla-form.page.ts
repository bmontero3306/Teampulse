import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, HostListener, computed, effect, inject, signal, untracked, viewChild } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom, forkJoin, of } from 'rxjs';

import { API } from '../../core/api';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import { CriterioFilaComponent } from './criterio-fila.component';
import {
  CHECKBOX_CSS,
  CompetenciaOpcion,
  CriterioEdicion,
  INPUT_CSS,
  PlantillaApi,
  PuestoOpcion,
  TEXTAREA_CSS,
  TIPOS_COMPETENCIA,
  TIPOS_PLANTILLA,
  erroresVacios,
  etiquetaPuesto,
  filaDesdeApi,
  listarTodo,
  normalizar,
  parsearErrores,
  type ErroresApi,
} from './evaluaciones-ui';

interface ModalCriterio {
  abierto: boolean;
  error: string;
  busqueda: string;
  competenciaId: number | null;
  elegidaNombre: string;
  crear: boolean;
  nombre: string;
  tipo: string;
  descripcion: string;
  categoria: string;
  tipoItem: 'escala' | 'texto';
  escalaMin: string;
  escalaMax: string;
  ponderacion: string;
  devEmpleado: boolean;
  devSupervisor: boolean;
  sugerencias: boolean;
  enviando: boolean;
}

function modalInicial(): ModalCriterio {
  return {
    abierto: false,
    error: '',
    busqueda: '',
    competenciaId: null,
    elegidaNombre: '',
    crear: false,
    nombre: '',
    tipo: 'tecnica',
    descripcion: '',
    categoria: '',
    tipoItem: 'escala',
    escalaMin: '1',
    escalaMax: '5',
    ponderacion: '0',
    devEmpleado: true,
    devSupervisor: true,
    sugerencias: false,
    enviando: false,
  };
}

@Component({
  selector: 'app-plantilla-form',
  imports: [ReactiveFormsModule, RouterLink, CriterioFilaComponent],
  template: `
    <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
      {{ plantillaId() ? 'Editar plantilla' : 'Nueva plantilla' }}
    </h1>
    <p class="mt-1 text-sm text-slate-600">
      Definí el tipo, las categorías, los criterios y los puestos que usan esta plantilla.
    </p>

    @if (errores().generales.length) {
      <ul class="mt-4 space-y-2">
        @for (error of errores().generales; track error) {
          <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
        }
      </ul>
    }

    @if (listo()) {
      <form class="mt-6 space-y-8" id="form-plantilla" [formGroup]="form" (ngSubmit)="guardar()">
        <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <h2 class="text-lg font-semibold text-slate-900">Datos de la plantilla</h2>
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            <div class="sm:col-span-2">
              <label class="mb-1 block text-sm font-medium text-slate-700" for="id-nombre">Nombre</label>
              <input id="id-nombre" type="text" formControlName="nombre" [class]="inputCss" />
              @if (mensajes('nombre'); as lista) {
                @if (lista.length) {
                  <ul class="errorlist">
                    @for (error of lista; track error) { <li>{{ error }}</li> }
                  </ul>
                }
              }
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700" for="id-tipo">Tipo</label>
              <select id="id-tipo" formControlName="tipo" [class]="inputCss">
                @for (tipo of tiposPlantilla; track tipo.value) {
                  <option [value]="tipo.value">{{ tipo.label }}</option>
                }
              </select>
              @if (mensajes('tipo'); as lista) {
                @if (lista.length) {
                  <ul class="errorlist">
                    @for (error of lista; track error) { <li>{{ error }}</li> }
                  </ul>
                }
              }
            </div>
            <div class="flex items-center gap-2">
              <input id="id-activa" type="checkbox" formControlName="activa" [class]="checkboxCss" />
              <label class="text-sm text-slate-700" for="id-activa">Plantilla activa</label>
            </div>
            <div class="sm:col-span-2">
              <label class="mb-1 block text-sm font-medium text-slate-700" for="id-descripcion">Descripción</label>
              <textarea id="id-descripcion" rows="4" formControlName="descripcion" [class]="textareaCss"></textarea>
              @if (mensajes('descripcion'); as lista) {
                @if (lista.length) {
                  <ul class="errorlist">
                    @for (error of lista; track error) { <li>{{ error }}</li> }
                  </ul>
                }
              }
            </div>
          </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">Puestos asociados</h2>
              <p class="text-sm text-slate-500">
                Si un puesto está asociado, esta plantilla gana sobre la del ciclo.
              </p>
            </div>
            <button
              type="button"
              id="btn-agregar-puesto"
              class="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
              (click)="mostrarBuscadorPuesto()"
            >
              Agregar puesto
            </button>
          </div>
          @if (mensajes('puestos'); as lista) {
            @if (lista.length) {
              <ul class="errorlist mt-3">
                @for (error of lista; track error) { <li>{{ error }}</li> }
              </ul>
            }
          }
          <div class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm" id="tabla-puestos">
              <thead class="border-b border-slate-200 text-slate-600">
                <tr>
                  <th class="py-2 pr-3 font-medium">Puesto</th>
                  <th class="py-2 pr-3 font-medium">Área</th>
                  <th class="py-2 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              @if (puestosAsociados().length) {
                <tbody>
                  @for (puesto of puestosAsociados(); track puesto.id) {
                    <tr class="border-b border-slate-100">
                      <td class="py-2 pr-3 text-slate-900">{{ puesto.nombre }}</td>
                      <td class="py-2 pr-3 text-slate-600">{{ puesto.area || '—' }}</td>
                      <td class="py-2 text-right">
                        <button
                          type="button"
                          class="rounded-lg px-2 py-1 text-sm font-medium text-red-700 hover:bg-red-50"
                          (click)="quitarPuesto(puesto.id)"
                        >
                          Quitar
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              } @else {
                <tbody id="puestos-vacio">
                  <tr>
                    <td colspan="3" class="px-4 py-8 text-center text-slate-500">
                      Todavía no hay puestos. Usá «Agregar puesto» para asociar uno.
                    </td>
                  </tr>
                </tbody>
              }
            </table>
          </div>
          <div class="relative mt-3 max-w-xl" #puestoBox [class.hidden]="!buscadorPuestoAbierto()">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="puesto-buscador">Buscar puesto</label>
            <input
              #busquedaPuesto
              type="search"
              id="puesto-buscador"
              autocomplete="off"
              placeholder="Escribí el nombre o el área…"
              [class]="inputCss"
              [value]="busquedaPuestoTexto()"
              (input)="alBuscarPuesto($event)"
              (focus)="mostrarSugerenciasPuesto()"
              (keydown)="teclaPuesto($event)"
            />
            <ul
              id="puesto-sugerencias"
              class="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
              [class.hidden]="!sugerenciasPuesto()"
              role="listbox"
            >
              @if (coincidenciasPuesto().length) {
                @for (puesto of coincidenciasPuesto(); track puesto.id) {
                  <li>
                    <button
                      type="button"
                      class="block w-full px-3 py-2 text-left text-sm text-slate-800 hover:bg-sky-50"
                      (click)="elegirPuesto(puesto.id)"
                    >
                      {{ etiquetaPuesto(puesto) }}
                    </button>
                  </li>
                }
              } @else {
                <li class="px-3 py-2 text-sm text-slate-500">{{ mensajeVacioPuesto() }}</li>
              }
            </ul>
            <button
              type="button"
              class="mt-2 text-sm font-medium text-slate-600 hover:text-slate-900"
              (click)="ocultarBuscadorPuesto()"
            >
              Cancelar
            </button>
          </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">Criterios</h2>
              <p class="text-sm text-slate-500">
                Vista compacta. Usá Editar para cambiar un criterio, o Agregar para crear uno nuevo.
              </p>
            </div>
            <button
              type="button"
              id="btn-agregar-criterio"
              class="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
              (click)="abrirModal()"
            >
              Agregar criterio
            </button>
          </div>

          @if (errores().criteriosGenerales.length) {
            <div class="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              @for (error of errores().criteriosGenerales; track error) {
                <p>{{ error }}</p>
              }
            </div>
          }

          <div class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm" id="tabla-criterios">
              <thead class="border-b border-slate-200 text-slate-600">
                <tr>
                  <th class="py-2 pr-3 font-medium">Competencia</th>
                  <th class="py-2 pr-3 font-medium">Categoría</th>
                  <th class="py-2 pr-3 font-medium">Tipo</th>
                  <th class="py-2 pr-3 font-medium">Escala</th>
                  <th class="py-2 pr-3 font-medium">Ponderación</th>
                  <th class="py-2 pr-3 font-medium">Devolución</th>
                  <th class="py-2 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              @for (criterio of criterios(); track criterio.key; let i = $index) {
                <tbody
                  appCriterioFila
                  [fila]="criterio"
                  [competencias]="competenciasVisibles()"
                  (cambio)="reemplazar(i, $event)"
                  (editar)="alternar(i)"
                  (quitar)="marcar(i, true)"
                  (deshacer)="marcar(i, false)"
                ></tbody>
              }
              @if (criterios().length === 0) {
                <tbody id="criterios-vacio">
                  <tr>
                    <td colspan="7" class="px-4 py-8 text-center text-slate-500">
                      Todavía no hay criterios. Agregá el primero para armar el formulario de evaluación.
                    </td>
                  </tr>
                </tbody>
              }
            </table>
          </div>
          <datalist id="categorias-plantilla">
            @for (categoria of categorias(); track categoria) {
              <option [value]="categoria"></option>
            }
          </datalist>
        </section>

        <div class="flex flex-wrap gap-3">
          <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
            Guardar
          </button>
          @if (plantillaId()) {
            <button
              type="button"
              class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              (click)="duplicar()"
            >
              Duplicar
            </button>
          }
          <a
            routerLink="/evaluaciones/plantillas"
            class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancelar
          </a>
        </div>
      </form>
    }

    @if (modal().abierto) {
      <div id="modal-criterio" class="fixed inset-0 z-50">
        <div class="absolute inset-0 bg-slate-900/40" (click)="cerrarModal()"></div>
        <div
          class="relative mx-auto mt-10 max-h-[calc(100vh-4rem)] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-xl sm:mt-16 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-criterio-titulo"
          #compBox
        >
          <h3 id="modal-criterio-titulo" class="text-lg font-semibold text-slate-900">Agregar criterio</h3>
          <p class="mt-1 text-sm text-slate-500">
            Elegí una competencia del catálogo o creá una nueva, y definí cómo se responde.
          </p>
          <p
            id="modal-criterio-error"
            class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            [class.hidden]="!modal().error"
          >
            {{ modal().error }}
          </p>
          <div class="mt-4 space-y-4">
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-competencia-busqueda">Competencia</label>
              <input
                #busquedaComp
                type="search"
                id="modal-competencia-busqueda"
                autocomplete="off"
                placeholder="Buscar en el catálogo…"
                [class]="inputCss"
                [value]="modal().busqueda"
                (input)="buscarCompetencia($event)"
                (focus)="mostrarSugerenciasCompetencia()"
              />
              <ul
                id="modal-competencia-sugerencias"
                class="mt-1 max-h-40 overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-sm"
                [class.hidden]="!modal().sugerencias || modal().crear"
              >
                @if (coincidenciasCompetencia().length) {
                  @for (comp of coincidenciasCompetencia(); track comp.id) {
                    <li>
                      <button
                        type="button"
                        class="block w-full px-3 py-2 text-left text-sm text-slate-800 hover:bg-sky-50"
                        (click)="elegirCompetencia(comp)"
                      >
                        {{ comp.nombre }}
                      </button>
                    </li>
                  }
                } @else {
                  <li class="px-3 py-2 text-sm text-slate-500">No hay competencias disponibles. Creá una nueva.</li>
                }
              </ul>
              <p id="modal-competencia-elegida" class="mt-2 text-sm text-slate-700" [class.hidden]="!modal().elegidaNombre">
                Seleccionada: {{ modal().elegidaNombre }}
              </p>
            </div>

            <div class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <label class="flex items-center gap-2 text-sm font-medium text-slate-800">
                <input
                  type="checkbox"
                  id="modal-crear-competencia"
                  [class]="checkboxCss"
                  [checked]="modal().crear"
                  (change)="toggleCrear($event)"
                />
                Crear una competencia nueva
              </label>
              <p class="mt-1 text-xs text-slate-500">Si no está en el catálogo, la creás acá y queda disponible para otras plantillas.</p>
              <div id="modal-alta-competencia" class="mt-3 space-y-3" [class.hidden]="!modal().crear">
                <div>
                  <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-comp-nombre">Nombre</label>
                  <input id="modal-comp-nombre" type="text" [class]="inputCss" [value]="modal().nombre" (input)="patchModal({ nombre: valor($event) })" />
                </div>
                <div>
                  <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-comp-tipo">Tipo</label>
                  <select id="modal-comp-tipo" [class]="inputCss" [value]="modal().tipo" (change)="patchModal({ tipo: valor($event) })">
                    @for (tipo of tiposCompetencia; track tipo.value) {
                      <option [value]="tipo.value">{{ tipo.label }}</option>
                    }
                  </select>
                </div>
                <div>
                  <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-comp-descripcion">Descripción (opcional)</label>
                  <textarea
                    id="modal-comp-descripcion"
                    rows="2"
                    [class]="inputCss"
                    [value]="modal().descripcion"
                    (input)="patchModal({ descripcion: valor($event) })"
                  ></textarea>
                </div>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-categoria">Categoría</label>
                <input
                  id="modal-categoria"
                  type="text"
                  list="categorias-plantilla"
                  placeholder="Ej. Competencias generales"
                  [class]="inputCss"
                  [value]="modal().categoria"
                  (input)="patchModal({ categoria: valor($event) })"
                />
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-tipo-item">Tipo de respuesta</label>
                <select id="modal-tipo-item" [class]="inputCss" [value]="modal().tipoItem" (change)="cambiarTipoModal($event)">
                  <option value="escala">Escala numérica (puntaje + devolución)</option>
                  <option value="texto">Solo texto (devolución, sin puntaje)</option>
                </select>
              </div>
              <div class="modal-campo-escala" [class.hidden]="modal().tipoItem === 'texto'">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-escala-min">Escala mínima</label>
                <input id="modal-escala-min" type="number" [class]="inputCss" [value]="modal().escalaMin" (input)="patchModal({ escalaMin: valor($event) })" />
              </div>
              <div class="modal-campo-escala" [class.hidden]="modal().tipoItem === 'texto'">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-escala-max">Escala máxima</label>
                <input id="modal-escala-max" type="number" [class]="inputCss" [value]="modal().escalaMax" (input)="patchModal({ escalaMax: valor($event) })" />
              </div>
              <div class="modal-campo-escala sm:col-span-2" [class.hidden]="modal().tipoItem === 'texto'">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="modal-ponderacion">Ponderación (%)</label>
                <input
                  id="modal-ponderacion"
                  type="number"
                  min="0"
                  step="0.01"
                  [class]="inputCss"
                  [value]="modal().ponderacion"
                  (input)="patchModal({ ponderacion: valor($event) })"
                />
              </div>
            </div>

            <label class="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                id="modal-dev-empleado"
                class="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                [checked]="modal().devEmpleado"
                (change)="patchModal({ devEmpleado: marcado($event) })"
              />
              <span>
                <span class="font-medium">Devolución del empleado obligatoria</span>
                <span class="block text-xs text-slate-500">El evaluado tiene que dejar un comentario en este ítem.</span>
              </span>
            </label>
            <label class="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                id="modal-dev-supervisor"
                class="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                [checked]="modal().devSupervisor"
                (change)="patchModal({ devSupervisor: marcado($event) })"
              />
              <span>
                <span class="font-medium">Devolución del supervisor obligatoria</span>
                <span class="block text-xs text-slate-500">El evaluador tiene que dejar feedback en este ítem.</span>
              </span>
            </label>
          </div>
          <div class="mt-6 flex flex-wrap justify-end gap-2">
            <button type="button" class="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100" (click)="cerrarModal()">
              Cancelar
            </button>
            <button
              type="button"
              id="modal-criterio-confirmar"
              class="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60"
              [disabled]="modal().enviando"
              (click)="confirmarModal()"
            >
              Agregar a la plantilla
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class PlantillaFormPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly title = inject(Title);
  private token = 0;
  private seq = 1;

  readonly inputCss = INPUT_CSS;
  readonly textareaCss = TEXTAREA_CSS;
  readonly checkboxCss = CHECKBOX_CSS;
  readonly tiposPlantilla = TIPOS_PLANTILLA;
  readonly tiposCompetencia = TIPOS_COMPETENCIA;
  readonly etiquetaPuesto = etiquetaPuesto;

  plantillaId = signal<number | null>(null);

  listo = signal(false);
  errores = signal<ErroresApi>(erroresVacios());
  competencias = signal<CompetenciaOpcion[]>([]);
  puestos = signal<PuestoOpcion[]>([]);
  puestosElegidos = signal<number[]>([]);
  criterios = signal<CriterioEdicion[]>([]);
  buscadorPuestoAbierto = signal(false);
  busquedaPuestoTexto = signal('');
  sugerenciasPuesto = signal(false);
  modal = signal<ModalCriterio>(modalInicial());

  nombre = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  form = new FormGroup({
    nombre: this.nombre,
    tipo: new FormControl('mixta', { nonNullable: true }),
    descripcion: new FormControl('', { nonNullable: true }),
    activa: new FormControl(true, { nonNullable: true }),
  });

  private readonly puestoBox = viewChild<ElementRef<HTMLElement>>('puestoBox');
  private readonly compBox = viewChild<ElementRef<HTMLElement>>('compBox');
  private readonly inputPuesto = viewChild<ElementRef<HTMLInputElement>>('busquedaPuesto');
  private readonly inputComp = viewChild<ElementRef<HTMLInputElement>>('busquedaComp');

  competenciasVisibles = computed(() => {
    const usados = new Set(
      this.criterios()
        .map((fila) => fila.competencia)
        .filter((id): id is number => id != null),
    );
    return this.competencias()
      .filter((comp) => comp.activa || usados.has(comp.id))
      .slice()
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  usadas = computed(() => {
    const ids = new Set<number>();
    for (const fila of this.criterios()) {
      if (!fila.quitar && fila.competencia != null) {
        ids.add(fila.competencia);
      }
    }
    return ids;
  });

  categorias = computed(() => {
    const vistos = new Set<string>();
    for (const fila of this.criterios()) {
      const valor = fila.categoria.trim();
      if (valor) {
        vistos.add(valor);
      }
    }
    return [...vistos];
  });

  puestosAsociados = computed(() => {
    const ids = new Set(this.puestosElegidos());
    return this.puestos()
      .filter((puesto) => ids.has(puesto.id))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  catalogoPuestos = computed(() => {
    const tomados = new Set(this.puestosElegidos());
    return this.puestos().filter((puesto) => puesto.activo || tomados.has(puesto.id));
  });

  coincidenciasPuesto = computed(() => {
    if (!this.buscadorPuestoAbierto()) {
      return [];
    }
    const q = normalizar(this.busquedaPuestoTexto());
    const tomados = new Set(this.puestosElegidos());
    return this.catalogoPuestos()
      .filter((puesto) => {
        if (tomados.has(puesto.id) || !puesto.activo) {
          return false;
        }
        if (!q) {
          return true;
        }
        return normalizar(puesto.nombre).includes(q) || normalizar(puesto.area).includes(q);
      })
      .slice(0, 12);
  });

  coincidenciasCompetencia = computed(() => {
    const modal = this.modal();
    if (!modal.sugerencias || modal.crear) {
      return [];
    }
    const q = normalizar(modal.busqueda);
    const usadas = this.usadas();
    return this.competenciasVisibles()
      .filter((comp) => {
        if (usadas.has(comp.id)) {
          return false;
        }
        if (!q) {
          return true;
        }
        return normalizar(comp.nombre).includes(q);
      })
      .slice(0, 12);
  });

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const raw = params.get('id');
      this.plantillaId.set(raw && /^\d+$/.test(raw) ? Number(raw) : null);
    });
    effect(() => {
      const id = this.plantillaId();
      this.title.setTitle(`${id ? 'Editar plantilla' : 'Nueva plantilla'} · TeamPulse`);
      untracked(() => this.cargar(id));
    });
  }

  @HostListener('document:click', ['$event'])
  clickDocumento(event: MouseEvent): void {
    const target = event.target as Node;
    const puesto = this.puestoBox()?.nativeElement;
    if (puesto && !puesto.contains(target)) {
      this.sugerenciasPuesto.set(false);
    }
    const comp = this.compBox()?.nativeElement;
    if (this.modal().abierto && comp && !comp.contains(target)) {
      this.patchModal({ sugerencias: false });
    }
  }

  @HostListener('document:keydown', ['$event'])
  teclaDocumento(event: KeyboardEvent): void {
    if (event.key !== 'Escape') {
      return;
    }
    if (this.buscadorPuestoAbierto()) {
      this.ocultarBuscadorPuesto();
      return;
    }
    if (this.modal().abierto) {
      this.cerrarModal();
    }
  }

  mensajes(campo: string): string[] {
    const servidor = this.errores().campos[campo] ?? [];
    if (servidor.length) {
      return servidor;
    }
    const control = this.form.get(campo);
    if (control?.touched && control.hasError('required')) {
      return ['Este campo es obligatorio.'];
    }
    return [];
  }

  mensajeVacioPuesto(): string {
    const catalogo = this.catalogoPuestos();
    if (!catalogo.length) {
      return 'No hay puestos activos en la empresa.';
    }
    const tomados = new Set(this.puestosElegidos());
    if (catalogo.every((puesto) => tomados.has(puesto.id))) {
      return 'Ya están todos los puestos agregados.';
    }
    return 'No hay puestos que coincidan.';
  }

  cargar(id: number | null): void {
    const token = ++this.token;
    this.listo.set(false);
    this.errores.set(erroresVacios());
    forkJoin({
      competencias: listarTodo<CompetenciaOpcion>(this.http, `${API}/competencias/`),
      puestos: listarTodo<{ id: number; nombre: string; area_nombre: string | null; activo: boolean }>(
        this.http,
        `${API}/puestos/`,
      ),
      plantilla: id ? this.http.get<PlantillaApi>(`${API}/plantillas/${id}/`) : of(null),
    }).subscribe({
      next: ({ competencias, puestos, plantilla }) => {
        if (token !== this.token) {
          return;
        }
        this.competencias.set(competencias);
        this.puestos.set(
          puestos
            .map((puesto) => ({
              id: puesto.id,
              nombre: puesto.nombre,
              area: puesto.area_nombre ?? '',
              activo: puesto.activo,
            }))
            .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
        );
        if (plantilla) {
          this.form.reset({
            nombre: plantilla.nombre,
            tipo: plantilla.tipo || 'mixta',
            descripcion: plantilla.descripcion ?? '',
            activa: plantilla.activa,
          });
          this.puestosElegidos.set(plantilla.puestos ?? []);
          this.criterios.set(
            (plantilla.criterios ?? []).map((criterio) => {
              const fila = filaDesdeApi(criterio, this.seq++);
              if (!fila.competenciaNombre && fila.competencia != null) {
                fila.competenciaNombre = competencias.find((comp) => comp.id === fila.competencia)?.nombre ?? '';
              }
              return fila;
            }),
          );
        } else {
          this.form.reset({ nombre: '', tipo: 'mixta', descripcion: '', activa: true });
          this.puestosElegidos.set([]);
          this.criterios.set([]);
        }
        this.buscadorPuestoAbierto.set(false);
        this.busquedaPuestoTexto.set('');
        this.sugerenciasPuesto.set(false);
        this.modal.set(modalInicial());
        this.listo.set(true);
      },
      error: (err) => {
        if (token !== this.token) {
          return;
        }
        this.alertas.error(mensajeError(err));
        this.listo.set(true);
      },
    });
  }

  mostrarBuscadorPuesto(): void {
    this.buscadorPuestoAbierto.set(true);
    this.busquedaPuestoTexto.set('');
    this.sugerenciasPuesto.set(true);
    setTimeout(() => this.inputPuesto()?.nativeElement.focus());
  }

  ocultarBuscadorPuesto(): void {
    this.buscadorPuestoAbierto.set(false);
    this.busquedaPuestoTexto.set('');
    this.sugerenciasPuesto.set(false);
  }

  mostrarSugerenciasPuesto(): void {
    this.sugerenciasPuesto.set(true);
  }

  alBuscarPuesto(event: Event): void {
    this.busquedaPuestoTexto.set((event.target as HTMLInputElement).value);
    this.sugerenciasPuesto.set(true);
  }

  teclaPuesto(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.sugerenciasPuesto.set(false);
    }
  }

  elegirPuesto(id: number): void {
    this.puestosElegidos.update((lista) => (lista.includes(id) ? lista : [...lista, id]));
    this.busquedaPuestoTexto.set('');
    this.sugerenciasPuesto.set(true);
    queueMicrotask(() => this.inputPuesto()?.nativeElement.focus());
  }

  quitarPuesto(id: number): void {
    this.puestosElegidos.update((lista) => lista.filter((item) => item !== id));
  }

  reemplazar(index: number, fila: CriterioEdicion): void {
    this.criterios.update((lista) => lista.map((item, i) => (i === index ? fila : item)));
  }

  alternar(index: number): void {
    this.criterios.update((lista) =>
      lista.map((item, i) => ({
        ...item,
        abierto: i === index ? !item.abierto : false,
      })),
    );
  }

  marcar(index: number, quitar: boolean): void {
    this.criterios.update((lista) =>
      lista.map((item, i) =>
        i === index ? { ...item, quitar, abierto: quitar ? false : item.abierto } : item,
      ),
    );
  }

  abrirModal(): void {
    this.modal.set({ ...modalInicial(), abierto: true });
    setTimeout(() => this.inputComp()?.nativeElement.focus());
  }

  cerrarModal(): void {
    this.modal.set(modalInicial());
  }

  patchModal(parcial: Partial<ModalCriterio>): void {
    this.modal.update((actual) => ({ ...actual, ...parcial }));
  }

  buscarCompetencia(event: Event): void {
    this.patchModal({
      busqueda: (event.target as HTMLInputElement).value,
      competenciaId: null,
      elegidaNombre: '',
      sugerencias: true,
    });
  }

  mostrarSugerenciasCompetencia(): void {
    if (!this.modal().crear) {
      this.patchModal({ sugerencias: true });
    }
  }

  elegirCompetencia(comp: CompetenciaOpcion): void {
    this.patchModal({
      competenciaId: comp.id,
      busqueda: comp.nombre,
      elegidaNombre: comp.nombre,
      sugerencias: false,
      crear: false,
    });
  }

  toggleCrear(event: Event): void {
    const crear = (event.target as HTMLInputElement).checked;
    this.patchModal({
      crear,
      sugerencias: crear ? false : this.modal().sugerencias,
      competenciaId: crear ? null : this.modal().competenciaId,
      elegidaNombre: crear ? '' : this.modal().elegidaNombre,
    });
    if (crear) {
      setTimeout(() => document.getElementById('modal-comp-nombre')?.focus());
    }
  }

  cambiarTipoModal(event: Event): void {
    const tipoItem = (event.target as HTMLSelectElement).value === 'texto' ? 'texto' : 'escala';
    this.patchModal({
      tipoItem,
      ponderacion: tipoItem === 'texto' ? '0' : this.modal().ponderacion,
    });
  }

  valor(event: Event): string {
    return (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value;
  }

  marcado(event: Event): boolean {
    return (event.target as HTMLInputElement).checked;
  }

  async confirmarModal(): Promise<void> {
    const modal = this.modal();
    this.patchModal({ error: '' });
    if (modal.tipoItem === 'escala') {
      if (Number(modal.escalaMin) >= Number(modal.escalaMax)) {
        this.patchModal({ error: 'La escala mínima debe ser menor que la máxima.' });
        return;
      }
      if (modal.ponderacion === '' || Number(modal.ponderacion) < 0) {
        this.patchModal({ error: 'Indicá una ponderación mayor o igual a 0.' });
        return;
      }
    }
    this.patchModal({ enviando: true });
    let competenciaId = modal.competenciaId;
    let nombre = modal.elegidaNombre;
    try {
      if (modal.crear) {
        const nombreNuevo = modal.nombre.trim();
        if (!nombreNuevo) {
          this.patchModal({ error: 'Escribí el nombre de la competencia nueva.', enviando: false });
          return;
        }
        const creada = await firstValueFrom(
          this.http.post<CompetenciaOpcion>(`${API}/competencias/`, {
            nombre: nombreNuevo,
            tipo: modal.tipo,
            descripcion: modal.descripcion,
            activa: true,
          }),
        );
        competenciaId = creada.id;
        nombre = creada.nombre;
        this.competencias.update((lista) => [...lista.filter((item) => item.id !== creada.id), creada]);
      }
      if (!competenciaId) {
        this.patchModal({ error: 'Elegí una competencia o creá una nueva.', enviando: false });
        return;
      }
      if (this.usadas().has(competenciaId)) {
        this.patchModal({ error: 'Esa competencia ya está en la plantilla.', enviando: false });
        return;
      }
      this.criterios.update((lista) => [
        ...lista,
        {
          key: this.seq++,
          competencia: competenciaId,
          competenciaNombre: nombre,
          categoria: modal.categoria,
          tipo_item: modal.tipoItem,
          orden: '',
          escala_min: modal.escalaMin || '1',
          escala_max: modal.escalaMax || '5',
          ponderacion: modal.tipoItem === 'texto' ? '0' : modal.ponderacion || '0',
          devEmpleado: modal.devEmpleado,
          devSupervisor: modal.devSupervisor,
          abierto: false,
          quitar: false,
          errorGeneral: '',
          errores: {},
        },
      ]);
      this.cerrarModal();
    } catch (err) {
      const parsed = parsearErrores(err);
      const texto = parsed.generales[0] || Object.values(parsed.campos)[0]?.[0] || 'No se pudo crear la competencia.';
      this.patchModal({ error: texto, enviando: false });
    }
  }

  duplicar(): void {
    const id = this.plantillaId();
    if (!id) {
      return;
    }
    this.http.post<PlantillaApi>(`${API}/plantillas/${id}/duplicar/`, {}).subscribe({
      next: (copia) => {
        this.alertas.success(`Se creó la plantilla «${copia.nombre}».`);
        void this.router.navigate(['/evaluaciones/plantillas', copia.id, 'editar']);
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  guardar(): void {
    this.form.markAllAsTouched();
    const locales = this.validarLocal();
    if (this.form.invalid || !locales) {
      return;
    }
    const raw = this.form.getRawValue();
    let ordenAuto = 1;
    const criterios = this.criterios()
      .filter((fila) => !fila.quitar)
      .map((fila) => {
        const orden = fila.orden.trim() ? Number(fila.orden) : ordenAuto;
        ordenAuto += 1;
        const tipoTexto = fila.tipo_item === 'texto';
        const item: Record<string, unknown> = {
          competencia: fila.competencia,
          categoria: fila.categoria,
          tipo_item: fila.tipo_item,
          orden,
          escala_min: Number(fila.escala_min || 1),
          escala_max: Number(fila.escala_max || 5),
          ponderacion: tipoTexto ? 0 : Number(fila.ponderacion || 0),
          comentario_empleado_obligatorio: fila.devEmpleado,
          comentario_supervisor_obligatorio: fila.devSupervisor,
        };
        if (fila.id) {
          item['id'] = fila.id;
        }
        return item;
      });
    const body = {
      nombre: raw.nombre,
      tipo: raw.tipo,
      descripcion: raw.descripcion,
      activa: raw.activa,
      puestos: this.puestosElegidos(),
      criterios,
    };
    const id = this.plantillaId();
    const req = id ? this.http.put(`${API}/plantillas/${id}/`, body) : this.http.post(`${API}/plantillas/`, body);
    req.subscribe({
      next: () => {
        this.alertas.success('Plantilla guardada correctamente.');
        void this.router.navigate(['/evaluaciones/plantillas']);
      },
      error: (err) => this.aplicarErrores(parsearErrores(err)),
    });
  }

  private validarLocal(): boolean {
    const errores = erroresVacios();
    if (this.plantillaId() == null && this.criterios().every((fila) => fila.quitar)) {
      errores.criteriosGenerales.push('La plantilla necesita al menos un criterio.');
    }
    const vistos = new Set<number>();
    let duplicada = false;
    const filas = this.criterios().map((fila) => {
      if (fila.quitar) {
        return { ...fila, errores: {}, errorGeneral: '' };
      }
      const campos: Record<string, string[]> = {};
      if (fila.competencia == null) {
        campos['competencia'] = ['Este campo es obligatorio.'];
      } else if (vistos.has(fila.competencia)) {
        duplicada = true;
      } else {
        vistos.add(fila.competencia);
      }
      if (fila.tipo_item === 'escala') {
        if (fila.escala_min !== '' && fila.escala_max !== '' && Number(fila.escala_min) >= Number(fila.escala_max)) {
          campos['escala_max'] = ['La escala mínima debe ser menor que la máxima.'];
        }
        if (fila.ponderacion !== '' && Number(fila.ponderacion) < 0) {
          campos['ponderacion'] = ['La ponderación no puede ser negativa.'];
        }
      }
      const tiene = Object.keys(campos).length > 0;
      return { ...fila, errores: campos, errorGeneral: '', abierto: tiene ? true : fila.abierto };
    });
    if (duplicada) {
      errores.criteriosGenerales.push('No se puede usar la misma competencia más de una vez.');
    }
    this.criterios.set(filas);
    this.errores.set(errores);
    return errores.criteriosGenerales.length === 0 && filas.every((fila) => !Object.keys(fila.errores).length);
  }

  private aplicarErrores(errores: ErroresApi): void {
    const indices: number[] = [];
    this.criterios().forEach((fila, index) => {
      if (!fila.quitar) {
        indices.push(index);
      }
    });
    this.criterios.update((lista) =>
      lista.map((fila, index) => {
        const pos = indices.indexOf(index);
        const info = pos >= 0 ? errores.filas[pos] : undefined;
        if (!info) {
          return { ...fila, errores: {}, errorGeneral: '' };
        }
        const tiene = info.generales.length > 0 || Object.values(info.campos).some((item) => item.length);
        return {
          ...fila,
          errores: info.campos,
          errorGeneral: info.generales[0] ?? '',
          abierto: tiene ? true : fila.abierto,
        };
      }),
    );
    this.errores.set(errores);
    const texto = errores.generales[0] || errores.criteriosGenerales[0];
    if (texto && !Object.keys(errores.campos).length && !Object.keys(errores.filas).length) {
      this.alertas.error(texto);
    }
  }
}
