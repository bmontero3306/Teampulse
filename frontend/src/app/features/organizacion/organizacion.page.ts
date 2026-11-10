import { HttpClient } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { Observable, combineLatest, forkJoin, of } from 'rxjs';
import { catchError, finalize, map, switchMap } from 'rxjs/operators';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { Pagina } from '../../core/models';
import { mensajeError } from '../../shared/errores';
import { NodoOrgComponent, NodoOrganigrama } from './organigrama-nodo.component';

type Seccion = 'organigrama' | 'puestos' | 'areas' | 'competencias';
type Vista = 'organigrama' | 'lista' | 'form';

interface Area {
  id: number;
  nombre: string;
  area_padre: number | null;
  area_padre_nombre: string | null;
  activa: boolean;
}

interface Puesto {
  id: number;
  nombre: string;
  descripcion: string;
  area: number | null;
  area_nombre: string | null;
  puesto_superior: number | null;
  puesto_superior_nombre: string | null;
  activo: boolean;
}

interface Competencia {
  id: number;
  nombre: string;
  descripcion: string;
  tipo: string;
  activa: boolean;
}

interface Plantilla {
  id: number;
  nombre: string;
  activa: boolean;
  puestos: number[];
}

interface NodoApi {
  id: number;
  nombre: string;
  area: string | null;
  descripcion?: string;
  hijos?: NodoApi[];
}

interface OrganigramaResp {
  raices: NodoApi[];
  sin_puesto: boolean;
}

interface Aviso {
  tipo: 'success' | 'error';
  texto: string;
}

const INPUT_CSS =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';
const TEXTAREA_CSS = `${INPUT_CSS} min-h-24`;
const CHECKBOX_CSS = 'h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500';

@Component({
  selector: 'app-organizacion',
  imports: [ReactiveFormsModule, RouterLink, NodoOrgComponent],
  template: `
    @if (aviso(); as aviso) {
      <ul class="mb-4 space-y-2">
        <li
          [class]="
            aviso.tipo === 'success'
              ? 'rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800'
              : 'rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800'
          "
        >
          {{ aviso.texto }}
        </li>
      </ul>
    }

    <nav class="mb-6 flex flex-wrap gap-2 text-sm">
      @for (tab of tabs; track tab.id) {
        <a
          [routerLink]="hrefSeccion(tab.id)"
          [class]="
            seccion() === tab.id
              ? 'rounded-lg px-3 py-1.5 font-medium bg-sky-100 text-sky-800'
              : 'rounded-lg px-3 py-1.5 font-medium text-slate-600 hover:bg-slate-100'
          "
        >
          {{ tab.label }}
        </a>
      }
    </nav>

    @if (seccion() === 'organigrama') {
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Organigrama</h1>
          <p class="mt-1 text-sm text-slate-600">Estructura de puestos de la empresa.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          @if (colapsable()) {
            <button
              type="button"
              id="org-expandir"
              class="inline-flex rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              (click)="expandirTodo()"
            >
              Expandir todo
            </button>
            <button
              type="button"
              id="org-colapsar"
              class="inline-flex rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              (click)="colapsarTodo()"
            >
              Colapsar todo
            </button>
          }
          @if (puedeEditar()) {
            <a
              routerLink="/organizacion/puestos/nuevo"
              class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
            >
              Nuevo puesto
            </a>
          }
        </div>
      </div>

      @if (organigramaLista() && sinPuesto()) {
        <p class="mt-8 rounded-xl border border-slate-200 bg-white px-4 py-6 text-slate-600">
          No tenés un puesto asignado. Cuando RRHH te asigne uno, vas a ver tu lugar en el organigrama.
        </p>
      } @else if (organigramaLista() && !raices().length) {
        <p class="mt-8 rounded-xl border border-slate-200 bg-white px-4 py-6 text-slate-600">
          Todavía no hay puestos activos para mostrar.
        </p>
      } @else if (organigramaLista()) {
        <div class="mt-6 overflow-x-auto">
          <ul id="organigrama-arbol" class="min-w-[18rem] space-y-3">
            @for (raiz of raices(); track raiz.id) {
              <app-nodo-org
                [nodo]="raiz"
                [abiertos]="abiertos()"
                [puedeEditar]="puedeEditar()"
                (alternar)="alternar($event)"
              />
            }
          </ul>
        </div>
      }
    } @else if (vista() === 'form' && seccion() === 'areas') {
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
        {{ editandoId() ? 'Editar área' : 'Nueva área' }}
      </h1>
      @if (avisosFormulario().length) {
        <ul id="errores-guardado" class="mt-4 space-y-2">
          @for (error of avisosFormulario(); track $index) {
            <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
          }
        </ul>
      }
      @if (formLista()) {
        <form class="mt-6 max-w-xl space-y-4 rounded-xl border border-slate-200 bg-white p-4 sm:p-6" [formGroup]="areaForm" (ngSubmit)="guardarArea()">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_nombre">Nombre</label>
            <input id="id_nombre" type="text" formControlName="nombre" maxlength="200" required [class]="inputCss" [attr.aria-invalid]="mensajes('nombre').length ? 'true' : null" />
            @if (mensajes('nombre').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_nombre_error">
                @for (error of mensajes('nombre'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_area_padre">Área padre</label>
            <select id="id_area_padre" formControlName="area_padre" [class]="inputCss" [attr.aria-invalid]="mensajes('area_padre').length ? 'true' : null">
              <option value="">— Sin área padre —</option>
              @for (area of areasPadre(); track area.id) {
                <option [value]="area.id">{{ area.nombre }}</option>
              }
            </select>
            @if (mensajes('area_padre').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_area_padre_error">
                @for (error of mensajes('area_padre'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div>
            <div class="flex items-center gap-2">
              <input id="id_activa" type="checkbox" formControlName="activa" [class]="checkboxCss" [attr.aria-invalid]="mensajes('activa').length ? 'true' : null" [attr.aria-describedby]="mensajes('activa').length ? 'id_activa_error' : null" />
              <label class="text-sm text-slate-700" for="id_activa">Área activa</label>
            </div>
            @if (mensajes('activa').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_activa_error">
                @for (error of mensajes('activa'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div class="flex flex-wrap gap-3 pt-2">
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
              Guardar
            </button>
            <a routerLink="/organizacion/areas" class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
              Cancelar
            </a>
          </div>
        </form>
      }
    } @else if (vista() === 'form' && seccion() === 'puestos') {
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
        {{ editandoId() ? 'Editar puesto' : 'Nuevo puesto' }}
      </h1>
      <p class="mt-1 text-sm text-slate-600">
        Asigná área y puesto superior. Las competencias, escalas y ponderación se definen en la plantilla de evaluación.
      </p>
      @if (avisosFormulario().length) {
        <ul id="errores-guardado" class="mt-4 space-y-2">
          @for (error of avisosFormulario(); track $index) {
            <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
          }
        </ul>
      }
      @if (formLista()) {
        <form class="mt-6 space-y-8" id="form-puesto" [formGroup]="puestoForm" (ngSubmit)="guardarPuesto()">
          <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-slate-900">Datos del puesto</h2>
            <div class="mt-4 grid gap-4 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="id_nombre">Nombre</label>
                <input id="id_nombre" type="text" formControlName="nombre" maxlength="200" required [class]="inputCss" [attr.aria-invalid]="mensajes('nombre').length ? 'true' : null" />
                @if (mensajes('nombre').length) {
                  <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_nombre_error">
                    @for (error of mensajes('nombre'); track $index) {
                      <li>{{ error }}</li>
                    }
                  </ul>
                }
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-slate-700" for="id_descripcion">Descripción</label>
                <textarea id="id_descripcion" formControlName="descripcion" rows="4" [class]="textareaCss" [attr.aria-invalid]="mensajes('descripcion').length ? 'true' : null"></textarea>
                @if (mensajes('descripcion').length) {
                  <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_descripcion_error">
                    @for (error of mensajes('descripcion'); track $index) {
                      <li>{{ error }}</li>
                    }
                  </ul>
                }
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="id_area">Área</label>
                <select id="id_area" formControlName="area" [class]="inputCss" [attr.aria-invalid]="mensajes('area').length ? 'true' : null">
                  <option value="">— Sin área —</option>
                  @for (area of areas(); track area.id) {
                    <option [value]="area.id">{{ area.nombre }}</option>
                  }
                </select>
                @if (mensajes('area').length) {
                  <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_area_error">
                    @for (error of mensajes('area'); track $index) {
                      <li>{{ error }}</li>
                    }
                  </ul>
                }
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700" for="id_puesto_superior">Puesto superior</label>
                <select id="id_puesto_superior" formControlName="puesto_superior" [class]="inputCss" [attr.aria-invalid]="mensajes('puesto_superior').length ? 'true' : null">
                  <option value="">— Sin puesto superior —</option>
                  @for (puesto of puestosSuperior(); track puesto.id) {
                    <option [value]="puesto.id">{{ puesto.nombre }}</option>
                  }
                </select>
                @if (mensajes('puesto_superior').length) {
                  <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_puesto_superior_error">
                    @for (error of mensajes('puesto_superior'); track $index) {
                      <li>{{ error }}</li>
                    }
                  </ul>
                }
              </div>
              <div class="sm:col-span-2">
                <div class="flex items-center gap-2">
                  <input id="id_activo" type="checkbox" formControlName="activo" [class]="checkboxCss" [attr.aria-invalid]="mensajes('activo').length ? 'true' : null" [attr.aria-describedby]="mensajes('activo').length ? 'id_activo_error' : null" />
                  <label class="text-sm text-slate-700" for="id_activo">Puesto activo</label>
                </div>
                @if (mensajes('activo').length) {
                  <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_activo_error">
                    @for (error of mensajes('activo'); track $index) {
                      <li>{{ error }}</li>
                    }
                  </ul>
                }
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
            <h2 class="text-lg font-semibold text-slate-900">Evaluación de este puesto</h2>
            <p class="mt-2 text-sm text-slate-600">
              Al activar un ciclo se usa la plantilla asociada a este puesto, si hay una activa.
              Si no, se usa la plantilla por defecto del ciclo.
            </p>
            @if (editandoId()) {
              @if (plantillasCargadas() && plantillasPuesto().length) {
                <ul class="mt-4 space-y-2 text-sm">
                  @for (plantilla of plantillasPuesto(); track plantilla.id) {
                    <li>
                      <a [routerLink]="['/evaluaciones/plantillas', plantilla.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-900">{{ plantilla.nombre }}</a>
                    </li>
                  }
                </ul>
              } @else if (plantillasCargadas() && plantillasOk()) {
                <p class="mt-4 text-sm text-slate-500">
                  Este puesto no tiene plantilla propia: se evaluará con la del ciclo.
                  Asociála desde
                  <a routerLink="/evaluaciones/plantillas" class="font-medium text-sky-700 hover:text-sky-900">Plantillas</a>.
                </p>
              }
            } @else {
              <p class="mt-4 text-sm text-slate-500">
                Después de guardar, asociá una plantilla desde
                <a routerLink="/evaluaciones/plantillas" class="font-medium text-sky-700 hover:text-sky-900">Plantillas</a>
                si este rol no debe usar la plantilla por defecto del ciclo.
              </p>
            }
          </section>

          <div class="flex flex-wrap gap-3">
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
              Guardar
            </button>
            <a routerLink="/organizacion/puestos" class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
              Cancelar
            </a>
          </div>
        </form>
      }
    } @else if (vista() === 'form' && seccion() === 'competencias') {
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
        {{ editandoId() ? 'Editar competencia' : 'Nueva competencia' }}
      </h1>
      @if (avisosFormulario().length) {
        <ul id="errores-guardado" class="mt-4 space-y-2">
          @for (error of avisosFormulario(); track $index) {
            <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
          }
        </ul>
      }
      @if (formLista()) {
        <form class="mt-6 max-w-xl space-y-4 rounded-xl border border-slate-200 bg-white p-4 sm:p-6" [formGroup]="competenciaForm" (ngSubmit)="guardarCompetencia()">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_nombre">Nombre</label>
            <input id="id_nombre" type="text" formControlName="nombre" maxlength="200" required [class]="inputCss" [attr.aria-invalid]="mensajes('nombre').length ? 'true' : null" />
            @if (mensajes('nombre').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_nombre_error">
                @for (error of mensajes('nombre'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_descripcion">Descripción</label>
            <textarea id="id_descripcion" formControlName="descripcion" rows="4" [class]="textareaCss" [attr.aria-invalid]="mensajes('descripcion').length ? 'true' : null"></textarea>
            @if (mensajes('descripcion').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_descripcion_error">
                @for (error of mensajes('descripcion'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="id_tipo">Tipo</label>
            <select id="id_tipo" formControlName="tipo" required [class]="inputCss" [attr.aria-invalid]="mensajes('tipo').length ? 'true' : null">
              @for (tipo of tiposCompetencia; track tipo.value) {
                <option [value]="tipo.value">{{ tipo.label }}</option>
              }
            </select>
            @if (mensajes('tipo').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_tipo_error">
                @for (error of mensajes('tipo'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div>
            <div class="flex items-center gap-2">
              <input id="id_activa" type="checkbox" formControlName="activa" [class]="checkboxCss" [attr.aria-invalid]="mensajes('activa').length ? 'true' : null" [attr.aria-describedby]="mensajes('activa').length ? 'id_activa_error' : null" />
              <label class="text-sm text-slate-700" for="id_activa">Competencia activa</label>
            </div>
            @if (mensajes('activa').length) {
              <ul class="mt-1 space-y-1 text-sm text-red-700" id="id_activa_error">
                @for (error of mensajes('activa'); track $index) {
                  <li>{{ error }}</li>
                }
              </ul>
            }
          </div>
          <div class="flex flex-wrap gap-3 pt-2">
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
              Guardar
            </button>
            <a routerLink="/organizacion/competencias" class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
              Cancelar
            </a>
          </div>
        </form>
      }
    } @else if (seccion() === 'areas') {
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Áreas</h1>
          <p class="mt-1 text-sm text-slate-600">Estructura de áreas de la empresa.</p>
        </div>
        @if (puedeEditar()) {
          <a routerLink="/organizacion/areas/nueva" class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
            Nueva área
          </a>
        }
      </div>
      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 font-medium">Nombre</th>
              <th class="px-4 py-3 font-medium">Área padre</th>
              <th class="px-4 py-3 font-medium">Estado</th>
              @if (puedeEditar()) {
                <th class="px-4 py-3 font-medium"></th>
              }
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (area of areas(); track area.id) {
              <tr>
                <td class="px-4 py-3 font-medium text-slate-900">{{ area.nombre }}</td>
                <td class="px-4 py-3 text-slate-600">{{ area.area_padre_nombre || '—' }}</td>
                <td class="px-4 py-3">
                  @if (area.activa) {
                    <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">Activa</span>
                  } @else {
                    <span class="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Inactiva</span>
                  }
                </td>
                @if (puedeEditar()) {
                  <td class="px-4 py-3 text-right">
                    <a [routerLink]="['/organizacion/areas', area.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-900">Editar</a>
                  </td>
                }
              </tr>
            } @empty {
              @if (listaLista()) {
                <tr>
                  <td colspan="4" class="px-4 py-8 text-center text-slate-500">No hay áreas para mostrar.</td>
                </tr>
              }
            }
          </tbody>
        </table>
      </div>
    } @else if (seccion() === 'puestos') {
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Puestos</h1>
          <p class="mt-1 text-sm text-slate-600">Definí la jerarquía. La evaluación de cada puesto sale de su plantilla o de la del ciclo.</p>
        </div>
        @if (puedeEditar()) {
          <a routerLink="/organizacion/puestos/nuevo" class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
            Nuevo puesto
          </a>
        }
      </div>
      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 font-medium">Nombre</th>
              <th class="px-4 py-3 font-medium">Área</th>
              <th class="px-4 py-3 font-medium">Superior</th>
              <th class="px-4 py-3 font-medium">Estado</th>
              @if (puedeEditar()) {
                <th class="px-4 py-3 font-medium"></th>
              }
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (puesto of puestos(); track puesto.id) {
              <tr>
                <td class="px-4 py-3 font-medium text-slate-900">{{ puesto.nombre }}</td>
                <td class="px-4 py-3 text-slate-600">{{ puesto.area_nombre || '—' }}</td>
                <td class="px-4 py-3 text-slate-600">{{ puesto.puesto_superior_nombre || '—' }}</td>
                <td class="px-4 py-3">
                  @if (puesto.activo) {
                    <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">Activo</span>
                  } @else {
                    <span class="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Inactivo</span>
                  }
                </td>
                @if (puedeEditar()) {
                  <td class="px-4 py-3 text-right">
                    <a [routerLink]="['/organizacion/puestos', puesto.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-900">Editar</a>
                  </td>
                }
              </tr>
            } @empty {
              @if (listaLista()) {
                <tr>
                  <td colspan="5" class="px-4 py-8 text-center text-slate-500">No hay puestos para mostrar.</td>
                </tr>
              }
            }
          </tbody>
        </table>
      </div>
    } @else {
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Competencias</h1>
          <p class="mt-1 text-sm text-slate-600">Catálogo para armar los criterios de las plantillas de evaluación.</p>
        </div>
        @if (puedeEditar()) {
          <a routerLink="/organizacion/competencias/nueva" class="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
            Nueva competencia
          </a>
        }
      </div>
      <div class="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 font-medium">Nombre</th>
              <th class="px-4 py-3 font-medium">Tipo</th>
              <th class="px-4 py-3 font-medium">Estado</th>
              @if (puedeEditar()) {
                <th class="px-4 py-3 font-medium"></th>
              }
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (competencia of competencias(); track competencia.id) {
              <tr>
                <td class="px-4 py-3 font-medium text-slate-900">{{ competencia.nombre }}</td>
                <td class="px-4 py-3 text-slate-600">{{ tipoLabel(competencia.tipo) }}</td>
                <td class="px-4 py-3">
                  @if (competencia.activa) {
                    <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800">Activa</span>
                  } @else {
                    <span class="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Inactiva</span>
                  }
                </td>
                @if (puedeEditar()) {
                  <td class="px-4 py-3 text-right">
                    <a [routerLink]="['/organizacion/competencias', competencia.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-900">Editar</a>
                  </td>
                }
              </tr>
            } @empty {
              @if (listaLista()) {
                <tr>
                  <td colspan="4" class="px-4 py-8 text-center text-slate-500">No hay competencias para mostrar.</td>
                </tr>
              }
            }
          </tbody>
        </table>
      </div>
    }
  `,
})
export class OrganizacionPage {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly title = inject(Title);
  private readonly destroyRef = inject(DestroyRef);

  readonly inputCss = INPUT_CSS;
  readonly textareaCss = TEXTAREA_CSS;
  readonly checkboxCss = CHECKBOX_CSS;
  readonly tabs: { id: Seccion; label: string }[] = [
    { id: 'organigrama', label: 'Organigrama' },
    { id: 'puestos', label: 'Puestos' },
    { id: 'areas', label: 'Áreas' },
    { id: 'competencias', label: 'Competencias' },
  ];
  readonly tiposCompetencia = [
    { value: 'tecnica', label: 'Técnica' },
    { value: 'actitudinal', label: 'Actitudinal' },
    { value: 'objetivo', label: 'Objetivo' },
    { value: 'otra', label: 'Otra' },
  ];

  readonly seccion = signal<Seccion>('organigrama');
  readonly vista = signal<Vista>('organigrama');
  readonly editandoId = signal<number | null>(null);
  readonly puedeEditar = computed(() => {
    const rol = this.auth.sesion()?.usuario.rol;
    return rol === 'superadmin' || rol === 'admin_rrhh';
  });
  readonly colapsable = computed(() => this.raices().some((nodo) => nodo.hijos.length > 0));

  readonly aviso = signal<Aviso | null>(null);
  readonly errores = signal<Record<string, string[]>>({});
  readonly generales = signal<string[]>([]);
  readonly raices = signal<NodoOrganigrama[]>([]);
  readonly sinPuesto = signal(false);
  readonly organigramaLista = signal(false);
  readonly abiertos = signal<ReadonlySet<number>>(new Set());
  readonly areas = signal<Area[]>([]);
  readonly puestos = signal<Puesto[]>([]);
  readonly competencias = signal<Competencia[]>([]);
  readonly listaLista = signal(false);
  readonly formLista = signal(false);
  readonly plantillasPuesto = signal<Plantilla[]>([]);
  readonly plantillasCargadas = signal(false);
  readonly plantillasOk = signal(true);

  readonly areaForm = new FormGroup({
    nombre: new FormControl('', { nonNullable: true }),
    area_padre: new FormControl('', { nonNullable: true }),
    activa: new FormControl(true, { nonNullable: true }),
  });
  readonly puestoForm = new FormGroup({
    nombre: new FormControl('', { nonNullable: true }),
    descripcion: new FormControl('', { nonNullable: true }),
    area: new FormControl('', { nonNullable: true }),
    puesto_superior: new FormControl('', { nonNullable: true }),
    activo: new FormControl(true, { nonNullable: true }),
  });
  readonly competenciaForm = new FormGroup({
    nombre: new FormControl('', { nonNullable: true }),
    descripcion: new FormControl('', { nonNullable: true }),
    tipo: new FormControl('tecnica', { nonNullable: true }),
    activa: new FormControl(true, { nonNullable: true }),
  });

  private token = 0;
  private enviando = false;

  constructor() {
    combineLatest([this.route.paramMap, this.route.queryParamMap])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(([, params]) => this.sincronizar(params));
  }

  hrefSeccion(seccion: Seccion): string {
    return seccion === 'organigrama' ? '/organizacion' : `/organizacion/${seccion}`;
  }

  mensajes(campo: string): string[] {
    return this.errores()[campo] ?? [];
  }

  avisosFormulario(): string[] {
    const destacados = ['area_padre', 'puesto_superior', 'activo', 'activa'];
    return [...this.generales(), ...destacados.flatMap((campo) => this.mensajes(campo))];
  }

  tipoLabel(tipo: string): string {
    return this.tiposCompetencia.find((item) => item.value === tipo)?.label ?? tipo;
  }

  areasPadre(): Area[] {
    const id = this.editandoId();
    return this.areas().filter((area) => area.id !== id);
  }

  puestosSuperior(): Puesto[] {
    const id = this.editandoId();
    return this.puestos().filter((puesto) => puesto.id !== id);
  }

  alternar(id: number): void {
    const siguiente = new Set(this.abiertos());
    if (siguiente.has(id)) {
      siguiente.delete(id);
    } else {
      siguiente.add(id);
    }
    this.abiertos.set(siguiente);
  }

  expandirTodo(): void {
    this.abiertos.set(new Set(this.idsConHijos(this.raices())));
  }

  colapsarTodo(): void {
    this.abiertos.set(new Set());
  }

  guardarArea(): void {
    const raw = this.areaForm.getRawValue();
    this.guardar(
      'areas',
      {
        nombre: raw.nombre,
        area_padre: this.idONull(raw.area_padre),
        activa: raw.activa,
      },
      'Área guardada correctamente.',
      'areas',
    );
  }

  guardarPuesto(): void {
    const raw = this.puestoForm.getRawValue();
    this.guardar(
      'puestos',
      {
        nombre: raw.nombre,
        descripcion: raw.descripcion,
        area: this.idONull(raw.area),
        puesto_superior: this.idONull(raw.puesto_superior),
        activo: raw.activo,
      },
      'Puesto guardado correctamente.',
      'puestos',
    );
  }

  guardarCompetencia(): void {
    const raw = this.competenciaForm.getRawValue();
    this.guardar(
      'competencias',
      {
        nombre: raw.nombre,
        descripcion: raw.descripcion,
        tipo: raw.tipo,
        activa: raw.activa,
      },
      'Competencia guardada correctamente.',
      'competencias',
    );
  }

  private sincronizar(params: ParamMap): void {
    if (this.redirigirQuery(params)) {
      return;
    }
    const { seccion, id, nuevo } = this.leerRuta();
    const pideFormulario = seccion !== 'organigrama' && (nuevo || id != null);

    if (pideFormulario && !this.puedeEditar()) {
      void this.router.navigateByUrl(this.hrefSeccion(seccion), { replaceUrl: true });
      return;
    }

    this.seccion.set(seccion);
    this.editandoId.set(pideFormulario && !nuevo ? id : null);
    this.vista.set(seccion === 'organigrama' ? 'organigrama' : pideFormulario ? 'form' : 'lista');
    this.errores.set({});
    this.generales.set([]);
    this.title.setTitle(`${this.tituloPagina()} · TeamPulse`);

    const state = window.history.state as { exito?: string; errorNav?: string };
    if (state?.errorNav) {
      this.aviso.set({ tipo: 'error', texto: state.errorNav });
      history.replaceState({ ...state, errorNav: undefined, exito: undefined }, '');
    } else if (state?.exito && !pideFormulario) {
      this.aviso.set({ tipo: 'success', texto: state.exito });
      history.replaceState({ ...state, exito: undefined, errorNav: undefined }, '');
    } else {
      this.aviso.set(null);
    }

    if (seccion === 'organigrama') {
      this.cargarOrganigrama();
      return;
    }
    if (pideFormulario) {
      this.cargarFormulario(seccion, nuevo ? null : id);
      return;
    }
    this.cargarLista(seccion);
  }

  private tituloPagina(): string {
    const seccion = this.seccion();
    const editando = this.editandoId();
    if (seccion === 'organigrama') {
      return 'Organigrama';
    }
    if (seccion === 'areas') {
      if (this.vista() !== 'form') {
        return 'Áreas';
      }
      return editando ? 'Editar área' : 'Nueva área';
    }
    if (seccion === 'puestos') {
      if (this.vista() !== 'form') {
        return 'Puestos';
      }
      return editando ? 'Editar puesto' : 'Nuevo puesto';
    }
    if (this.vista() !== 'form') {
      return 'Competencias';
    }
    return editando ? 'Editar competencia' : 'Nueva competencia';
  }

  private cargarOrganigrama(): void {
    const token = ++this.token;
    this.organigramaLista.set(false);
    this.sinPuesto.set(false);
    this.raices.set([]);
    this.abiertos.set(new Set());
    forkJoin({
      org: this.http.get<OrganigramaResp>(`${API}/organigrama/`),
      puestos: this.listar<Puesto>('puestos').pipe(catchError(() => of([] as Puesto[]))),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ org, puestos }) => {
          if (token !== this.token) {
            return;
          }
          const descripciones = new Map(puestos.map((puesto) => [puesto.id, puesto.descripcion ?? '']));
          this.raices.set((org.raices ?? []).map((nodo) => this.enriquecer(nodo, descripciones)));
          this.sinPuesto.set(!!org.sin_puesto);
          this.organigramaLista.set(true);
        },
        error: (err) => {
          if (token !== this.token) {
            return;
          }
          this.organigramaLista.set(true);
          this.aviso.set({ tipo: 'error', texto: mensajeError(err) });
        },
      });
  }

  private cargarLista(seccion: Exclude<Seccion, 'organigrama'>): void {
    const token = ++this.token;
    this.listaLista.set(false);
    if (seccion === 'areas') {
      this.areas.set([]);
    } else if (seccion === 'puestos') {
      this.puestos.set([]);
    } else {
      this.competencias.set([]);
    }
    this.listar<Area | Puesto | Competencia>(seccion)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          if (token !== this.token) {
            return;
          }
          if (seccion === 'areas') {
            this.areas.set(items as Area[]);
          } else if (seccion === 'puestos') {
            this.puestos.set(items as Puesto[]);
          } else {
            this.competencias.set(items as Competencia[]);
          }
          this.listaLista.set(true);
        },
        error: (err) => {
          if (token !== this.token) {
            return;
          }
          this.listaLista.set(true);
          this.aviso.set({ tipo: 'error', texto: mensajeError(err) });
        },
      });
  }

  private cargarFormulario(seccion: Exclude<Seccion, 'organigrama'>, id: number | null): void {
    const token = ++this.token;
    this.formLista.set(false);
    this.plantillasCargadas.set(false);
    this.plantillasOk.set(true);
    this.plantillasPuesto.set([]);

    if (seccion === 'competencias') {
      if (id == null) {
        this.competenciaForm.reset({ nombre: '', descripcion: '', tipo: 'tecnica', activa: true });
        this.formLista.set(true);
        return;
      }
      this.http
        .get<Competencia>(`${API}/competencias/${id}/`)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (competencia) => {
            if (token !== this.token) {
              return;
            }
            this.competenciaForm.reset({
              nombre: competencia.nombre,
              descripcion: competencia.descripcion ?? '',
              tipo: competencia.tipo,
              activa: competencia.activa,
            });
            this.formLista.set(true);
          },
          error: (err) => this.falloForm(token, err, seccion),
        });
      return;
    }

    if (seccion === 'areas') {
      const detalle$ = id == null ? of(null) : this.http.get<Area>(`${API}/areas/${id}/`);
      forkJoin({ areas: this.listar<Area>('areas'), detalle: detalle$ })
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: ({ areas, detalle }) => {
            if (token !== this.token) {
              return;
            }
            this.areas.set(areas);
            this.areaForm.reset({
              nombre: detalle?.nombre ?? '',
              area_padre: detalle?.area_padre != null ? String(detalle.area_padre) : '',
              activa: detalle?.activa ?? true,
            });
            this.formLista.set(true);
          },
          error: (err) => this.falloForm(token, err, seccion),
        });
      return;
    }

    const detalle$ = id == null ? of(null) : this.http.get<Puesto>(`${API}/puestos/${id}/`);
    const plantillas$ =
      id == null
        ? of({ ok: true, items: [] as Plantilla[] })
        : this.listar<Plantilla>('plantillas').pipe(
            map((items) => ({ ok: true, items })),
            catchError(() => of({ ok: false, items: [] as Plantilla[] })),
          );
    forkJoin({
      areas: this.listar<Area>('areas'),
      puestos: this.listar<Puesto>('puestos'),
      detalle: detalle$,
      plantillas: plantillas$,
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ areas, puestos, detalle, plantillas }) => {
          if (token !== this.token) {
            return;
          }
          this.areas.set(areas);
          this.puestos.set(puestos);
          this.puestoForm.reset({
            nombre: detalle?.nombre ?? '',
            descripcion: detalle?.descripcion ?? '',
            area: detalle?.area != null ? String(detalle.area) : '',
            puesto_superior: detalle?.puesto_superior != null ? String(detalle.puesto_superior) : '',
            activo: detalle?.activo ?? true,
          });
          this.plantillasOk.set(plantillas.ok);
          this.plantillasPuesto.set(
            plantillas.items
              .filter((plantilla) => plantilla.activa && id != null && plantilla.puestos?.includes(id))
              .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
          );
          this.plantillasCargadas.set(true);
          this.formLista.set(true);
        },
        error: (err) => this.falloForm(token, err, seccion),
      });
  }

  private falloForm(token: number, err: unknown, seccion: Seccion): void {
    if (token !== this.token) {
      return;
    }
    void this.router.navigateByUrl(this.hrefSeccion(seccion), { state: { errorNav: mensajeError(err) } });
  }

  private guardar(path: string, body: unknown, mensaje: string, seccion: Seccion): void {
    if (this.enviando) {
      return;
    }
    this.enviando = true;
    this.errores.set({});
    this.generales.set([]);
    const id = this.editandoId();
    const req =
      id == null
        ? this.http.post(`${API}/${path}/`, body)
        : this.http.patch(`${API}/${path}/${id}/`, body);
    req.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.enviando = false))).subscribe({
      next: () => {
        void this.router.navigateByUrl(this.hrefSeccion(seccion), { state: { exito: mensaje } });
      },
      error: (err) => this.aplicarError(err),
    });
  }

  private aplicarError(error: unknown): void {
    const data = (error as { error?: unknown }).error;
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      this.generales.set([mensajeError(error)]);
      this.errores.set({});
      this.enfocarErrores();
      return;
    }
    const campos: Record<string, string[]> = {};
    const generales: string[] = [];
    for (const [clave, valor] of Object.entries(data as Record<string, unknown>)) {
      const textos = textosDe(valor);
      if (!textos.length) {
        continue;
      }
      if (clave === 'non_field_errors' || clave === 'detail') {
        generales.push(...textos);
      } else {
        campos[clave] = textos;
      }
    }
    if (!generales.length && !Object.keys(campos).length) {
      generales.push(mensajeError(error));
    }
    this.generales.set(generales);
    this.errores.set(campos);
    this.enfocarErrores();
  }

  private enfocarErrores(): void {
    setTimeout(() => {
      document.getElementById('errores-guardado')?.scrollIntoView({ block: 'nearest' });
    });
  }

  private listar<T>(path: string, page = 1, acc: T[] = []): Observable<T[]> {
    return this.http.get<Pagina<T> | T[]>(`${API}/${path}/`, { params: { page, page_size: 100 } }).pipe(
      switchMap((data) => {
        if (Array.isArray(data)) {
          return of(acc.concat(data));
        }
        const todos = acc.concat(data.results ?? []);
        return data.next ? this.listar<T>(path, page + 1, todos) : of(todos);
      }),
    );
  }

  private enriquecer(nodo: NodoApi, descripciones: Map<number, string>): NodoOrganigrama {
    const descripcion = descripciones.has(nodo.id) ? (descripciones.get(nodo.id) ?? '') : (nodo.descripcion ?? '');
    return {
      id: nodo.id,
      nombre: nodo.nombre,
      area: nodo.area,
      descripcion,
      hijos: (nodo.hijos ?? []).map((hijo) => this.enriquecer(hijo, descripciones)),
    };
  }

  private idsConHijos(nodos: NodoOrganigrama[], acc: number[] = []): number[] {
    for (const nodo of nodos) {
      if (nodo.hijos.length) {
        acc.push(nodo.id);
        this.idsConHijos(nodo.hijos, acc);
      }
    }
    return acc;
  }

  private leerRuta(): { seccion: Seccion; id: number | null; nuevo: boolean } {
    const partes = this.router.url.split('?')[0].split('/').filter(Boolean);
    const seccionRaw = partes[1];
    const seccion: Seccion =
      seccionRaw === 'puestos' || seccionRaw === 'areas' || seccionRaw === 'competencias' ? seccionRaw : 'organigrama';
    if (seccion === 'organigrama') {
      return { seccion, id: null, nuevo: false };
    }
    const accion = partes[2];
    if (accion === 'nueva' || accion === 'nuevo') {
      return { seccion, id: null, nuevo: true };
    }
    if (accion && /^\d+$/.test(accion) && partes[3] === 'editar') {
      return { seccion, id: Number(accion), nuevo: false };
    }
    return { seccion, id: null, nuevo: false };
  }

  private redirigirQuery(params: ParamMap): boolean {
    const seccionRaw = params.get('seccion');
    if (seccionRaw !== 'puestos' && seccionRaw !== 'areas' && seccionRaw !== 'competencias' && seccionRaw !== 'organigrama') {
      return false;
    }
    const seccion: Seccion = seccionRaw;
    const id = this.leerIdQuery(params);
    const nuevo = params.get('nuevo') === '1' && id == null;
    let destino = this.hrefSeccion(seccion);
    if (seccion !== 'organigrama' && nuevo) {
      destino = seccion === 'puestos' ? `${destino}/nuevo` : `${destino}/nueva`;
    } else if (seccion !== 'organigrama' && id != null) {
      destino = `${destino}/${id}/editar`;
    }
    void this.router.navigateByUrl(destino, { replaceUrl: true });
    return true;
  }

  private leerIdQuery(params: ParamMap): number | null {
    const raw = params.get('id');
    if (!raw || !/^\d+$/.test(raw)) {
      return null;
    }
    return Number(raw);
  }

  private idONull(valor: string): number | null {
    return valor ? Number(valor) : null;
  }
}

function textosDe(valor: unknown): string[] {
  if (typeof valor === 'string') {
    return [valor];
  }
  if (Array.isArray(valor)) {
    return valor.flatMap((item) => textosDe(item));
  }
  if (valor && typeof valor === 'object') {
    return Object.values(valor).flatMap((item) => textosDe(item));
  }
  return [];
}
