import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { API } from '../../core/api';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import {
  AreaOpcion,
  CicloApi,
  INPUT_CSS,
  PlantillaApi,
  TEXTAREA_CSS,
  erroresVacios,
  listarTodo,
  parsearErrores,
  type ErroresApi,
} from './evaluaciones-ui';

@Component({
  selector: 'app-ciclo-form',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Nuevo ciclo</h1>
    <p class="mt-1 text-sm text-slate-600">Se crea en borrador. La activación genera las evaluaciones.</p>

    @if (errores().generales.length) {
      <ul class="mt-4 space-y-2">
        @for (error of errores().generales; track error) {
          <li class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{{ error }}</li>
        }
      </ul>
    }

    <form class="mt-6 space-y-6" [formGroup]="form" (ngSubmit)="guardar()">
      <section class="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="sm:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-nombre">Nombre</label>
            <input id="ciclo-nombre" type="text" formControlName="nombre" [class]="inputCss" />
            @if (mensajes('nombre'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-inicio">Fecha de inicio</label>
            <input id="ciclo-inicio" type="date" formControlName="fecha_inicio" [class]="inputCss" />
            @if (mensajes('fecha_inicio'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-cierre">Fecha de cierre</label>
            <input id="ciclo-cierre" type="date" formControlName="fecha_cierre" [class]="inputCss" />
            @if (mensajes('fecha_cierre'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="sm:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-plantilla">Plantilla por defecto</label>
            <select id="ciclo-plantilla" formControlName="plantilla_default" [class]="inputCss">
              <option [ngValue]="null">— Elegir plantilla —</option>
              @for (plantilla of plantillas(); track plantilla.id) {
                <option [ngValue]="plantilla.id">{{ plantilla.nombre }}</option>
              }
            </select>
            @if (mensajes('plantilla_default'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="sm:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-areas">Áreas</label>
            <p class="mb-1 text-xs text-slate-500">Si no seleccionás áreas, el ciclo incluye a toda la empresa.</p>
            <select id="ciclo-areas" multiple size="6" formControlName="areas" [class]="inputCss + ' min-h-32'">
              @for (area of areas(); track area.id) {
                <option [ngValue]="area.id">{{ area.nombre }}</option>
              }
            </select>
            @if (mensajes('areas'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
          <div class="sm:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700" for="ciclo-criterios">Criterios generales</label>
            <textarea id="ciclo-criterios" rows="4" formControlName="criterios_generales" [class]="textareaCss"></textarea>
            @if (mensajes('criterios_generales'); as lista) {
              @if (lista.length) {
                <ul class="errorlist">
                  @for (error of lista; track error) { <li>{{ error }}</li> }
                </ul>
              }
            }
          </div>
        </div>
      </section>
      <div class="flex flex-wrap gap-3">
        <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
          Guardar borrador
        </button>
        <a
          routerLink="/evaluaciones/ciclos"
          class="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
        >
          Cancelar
        </a>
      </div>
    </form>
  `,
})
export class CicloFormPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  private readonly router = inject(Router);
  private readonly title = inject(Title);

  readonly inputCss = INPUT_CSS;
  readonly textareaCss = TEXTAREA_CSS;

  errores = signal<ErroresApi>(erroresVacios());
  plantillas = signal<PlantillaApi[]>([]);
  areas = signal<AreaOpcion[]>([]);

  form = new FormGroup({
    nombre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    fecha_inicio: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    fecha_cierre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    plantilla_default: new FormControl<number | null>(null, { validators: [Validators.required] }),
    areas: new FormControl<number[]>([], { nonNullable: true }),
    criterios_generales: new FormControl('', { nonNullable: true }),
  });

  constructor() {
    this.title.setTitle('Nuevo ciclo · TeamPulse');
    forkJoin({
      plantillas: listarTodo<PlantillaApi>(this.http, `${API}/plantillas/`),
      areas: listarTodo<AreaOpcion>(this.http, `${API}/areas/`),
    }).subscribe({
      next: ({ plantillas, areas }) => {
        this.plantillas.set(plantillas.filter((item) => item.activa));
        this.areas.set(areas.filter((item) => item.activa));
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  mensajes(campo: string): string[] {
    const servidor = this.errores().campos[campo] ?? [];
    if (servidor.length) {
      return servidor;
    }
    const control = this.form.get(campo);
    if (control?.touched && control.invalid) {
      if (control.hasError('required')) {
        return ['Este campo es obligatorio.'];
      }
    }
    return [];
  }

  guardar(): void {
    this.form.markAllAsTouched();
    const errores = erroresVacios();
    const raw = this.form.getRawValue();
    if (raw.fecha_inicio && raw.fecha_cierre && raw.fecha_cierre < raw.fecha_inicio) {
      errores.campos['fecha_cierre'] = ['La fecha de cierre no puede ser anterior al inicio.'];
    }
    this.errores.set(errores);
    if (this.form.invalid || errores.campos['fecha_cierre']) {
      return;
    }
    const areas = (raw.areas ?? []).map((id) => Number(id));
    this.http
      .post<CicloApi>(`${API}/ciclos/`, {
        nombre: raw.nombre,
        fecha_inicio: raw.fecha_inicio,
        fecha_cierre: raw.fecha_cierre,
        plantilla_default: Number(raw.plantilla_default),
        areas,
        criterios_generales: raw.criterios_generales,
      })
      .subscribe({
        next: (ciclo) => {
          this.alertas.success('Ciclo creado en borrador.');
          void this.router.navigate(['/evaluaciones/ciclos', ciclo.id]);
        },
        error: (err) => {
          const parsed = parsearErrores(err);
          this.errores.set(parsed);
          if (parsed.generales.length && !Object.keys(parsed.campos).length) {
            this.alertas.error(parsed.generales.join(' '));
          }
        },
      });
  }
}
