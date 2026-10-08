import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';
import { AlertService } from '../../shared/alert.service';
import { BadgeComponent } from '../../shared/badge.component';
import { ButtonComponent } from '../../shared/button.component';
import { mensajeError } from '../../shared/errores';
import { InputDateComponent } from '../../shared/input-date.component';
import { InputTextComponent } from '../../shared/input-text.component';
import { ModalComponent } from '../../shared/modal.component';

interface Criterio {
  id?: number;
  competencia: number | null;
  categoria: string;
  tipo_item: string;
  orden: number;
  escala_min: number;
  escala_max: number;
  ponderacion: number;
  comentario_empleado_obligatorio: boolean;
  comentario_supervisor_obligatorio: boolean;
}

interface Plantilla {
  id: number;
  nombre: string;
  tipo: string;
  descripcion: string;
  activa: boolean;
  puestos: number[];
  criterios: Criterio[];
}

interface Ciclo {
  id: number;
  nombre: string;
  fecha_inicio: string;
  fecha_cierre: string;
  estado: string;
  plantilla_default: number;
  plantilla_nombre: string;
  areas: number[];
  criterios_generales: string;
  total_evals?: number;
  sin_evaluador_count?: number;
}

@Component({
  selector: 'app-plantillas',
  imports: [ReactiveFormsModule, ButtonComponent, InputTextComponent, BadgeComponent],
  template: `
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Plantillas</h1>
      <app-button label="Nueva" (buttonClick)="nueva()" />
    </div>
    <ul class="mt-4 divide-y rounded-xl border border-slate-200 bg-white">
      @for (plantilla of plantillas(); track plantilla.id) {
        <li class="flex items-center justify-between px-4 py-3 text-sm">
          <span>{{ plantilla.nombre }} <app-badge [label]="plantilla.tipo" /></span>
          <span class="flex gap-3">
            <button type="button" class="text-sky-700" (click)="editar(plantilla)">Editar</button>
            <button type="button" class="text-slate-600" (click)="duplicar(plantilla)">Duplicar</button>
          </span>
        </li>
      }
    </ul>
    @if (abierta()) {
      <form class="mt-6 space-y-3 rounded-xl border border-slate-200 bg-white p-4" [formGroup]="form" (ngSubmit)="guardar()">
        <app-input-text label="Nombre" [control]="nombre" />
        <label class="block text-sm">Tipo
          <select formControlName="tipo" class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
            <option value="mixta">Mixta</option>
            <option value="tecnica">Técnica</option>
            <option value="actitudinal">Actitudinal</option>
            <option value="objetivos">Objetivos</option>
          </select>
        </label>
        <h2 class="pt-2 font-medium">Criterios</h2>
        @for (criterio of criterios(); track $index) {
          <div class="grid gap-2 rounded-lg border border-slate-100 p-3 md:grid-cols-4">
            <label class="text-sm md:col-span-2">Competencia
              <select class="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2" [value]="criterio.competencia ?? ''" (change)="criterio.competencia = numero($event)">
                <option value="">Elegir</option>
                @for (comp of competencias(); track comp.id) {
                  <option [value]="comp.id">{{ comp.nombre }}</option>
                }
              </select>
            </label>
            <label class="text-sm">Tipo
              <select class="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2" [value]="criterio.tipo_item" (change)="criterio.tipo_item = valor($event)">
                <option value="escala">Escala</option>
                <option value="texto">Texto</option>
              </select>
            </label>
            <label class="text-sm">Ponderación
              <input type="number" class="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2" [value]="criterio.ponderacion" (input)="criterio.ponderacion = numero($event) ?? 0" />
            </label>
          </div>
        }
        <h2 class="pt-2 font-medium">Puestos</h2>
        <div class="flex flex-wrap gap-3 text-sm">
          @for (puesto of puestos(); track puesto.id) {
            <label class="flex items-center gap-2">
              <input type="checkbox" [checked]="puestosElegidos().includes(puesto.id)" (change)="togglePuesto(puesto.id)" />
              {{ puesto.nombre }}
            </label>
          }
        </div>
        <app-button color="secondary" label="Agregar criterio" (buttonClick)="agregarCriterio()" />
        <app-button type="submit" label="Guardar plantilla" />
      </form>
    }
  `,
})
export class PlantillasPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  plantillas = signal<Plantilla[]>([]);
  competencias = signal<{ id: number; nombre: string }[]>([]);
  puestos = signal<{ id: number; nombre: string }[]>([]);
  puestosElegidos = signal<number[]>([]);
  abierta = signal(false);
  editando = signal<number | null>(null);
  criterios = signal<Criterio[]>([]);
  nombre = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  form = new FormGroup({
    nombre: this.nombre,
    tipo: new FormControl('mixta', { nonNullable: true }),
    descripcion: new FormControl('', { nonNullable: true }),
    activa: new FormControl(true, { nonNullable: true }),
  });

  constructor() {
    this.cargar();
    this.http.get<Pagina<{ id: number; nombre: string }>>(`${API}/competencias/`).subscribe((p) => this.competencias.set(p.results));
    this.http.get<Pagina<{ id: number; nombre: string }>>(`${API}/puestos/`).subscribe((p) => this.puestos.set(p.results));
  }

  cargar(): void {
    this.http.get<Pagina<Plantilla>>(`${API}/plantillas/`).subscribe((p) => this.plantillas.set(p.results));
  }

  nueva(): void {
    this.editando.set(null);
    this.puestosElegidos.set([]);
    this.criterios.set([this.criterioVacio(1)]);
    this.form.reset({ tipo: 'mixta', activa: true, nombre: '', descripcion: '' });
    this.abierta.set(true);
  }

  editar(plantilla: Plantilla): void {
    this.http.get<Plantilla>(`${API}/plantillas/${plantilla.id}/`).subscribe((detalle) => {
      this.editando.set(detalle.id);
      this.form.patchValue(detalle);
      this.puestosElegidos.set(detalle.puestos);
      this.criterios.set(detalle.criterios);
      this.abierta.set(true);
    });
  }

  agregarCriterio(): void {
    this.criterios.update((lista) => [...lista, this.criterioVacio(lista.length + 1)]);
  }

  numero(event: Event): number | null {
    const value = (event.target as HTMLInputElement).value;
    return value ? Number(value) : null;
  }

  valor(event: Event): string {
    return (event.target as HTMLSelectElement).value;
  }

  togglePuesto(id: number): void {
    this.puestosElegidos.update((lista) => (lista.includes(id) ? lista.filter((item) => item !== id) : [...lista, id]));
  }

  guardar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const body = { ...this.form.getRawValue(), puestos: this.puestosElegidos(), criterios: this.criterios() };
    const id = this.editando();
    const req = id ? this.http.put(`${API}/plantillas/${id}/`, body) : this.http.post(`${API}/plantillas/`, body);
    req.subscribe({
      next: () => {
        this.alertas.success('Plantilla guardada.');
        this.abierta.set(false);
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  duplicar(plantilla: Plantilla): void {
    this.http.post(`${API}/plantillas/${plantilla.id}/duplicar/`, {}).subscribe({
      next: () => {
        this.alertas.success('Plantilla duplicada.');
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  private criterioVacio(orden: number): Criterio {
    return {
      competencia: null,
      categoria: '',
      tipo_item: 'escala',
      orden,
      escala_min: 1,
      escala_max: 5,
      ponderacion: 0,
      comentario_empleado_obligatorio: true,
      comentario_supervisor_obligatorio: true,
    };
  }
}

@Component({
  selector: 'app-ciclos',
  imports: [ReactiveFormsModule, RouterLink, ButtonComponent, InputTextComponent, InputDateComponent, BadgeComponent],
  template: `
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Ciclos</h1>
      <app-button label="Nuevo ciclo" (buttonClick)="nuevo()" />
    </div>
    <ul class="mt-4 divide-y rounded-xl border border-slate-200 bg-white">
      @for (ciclo of ciclos(); track ciclo.id) {
        <li class="flex items-center justify-between px-4 py-3 text-sm">
          <a [routerLink]="['/evaluaciones/ciclos', ciclo.id]" class="font-medium text-sky-800">{{ ciclo.nombre }}</a>
          <app-badge [label]="ciclo.estado" [tono]="ciclo.estado === 'activo' ? 'ok' : 'info'" />
        </li>
      }
    </ul>
    @if (abierto()) {
      <form class="mt-6 max-w-lg space-y-3" [formGroup]="form" (ngSubmit)="guardar()">
        <app-input-text label="Nombre" [control]="nombre" />
        <app-input-date label="Inicio" [control]="inicio" />
        <app-input-date label="Cierre" [control]="cierre" />
        <label class="block text-sm">Plantilla
          <select formControlName="plantilla_default" class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
            @for (plantilla of plantillas(); track plantilla.id) {
              <option [value]="plantilla.id">{{ plantilla.nombre }}</option>
            }
          </select>
        </label>
        <app-button type="submit" label="Crear borrador" />
      </form>
    }
  `,
})
export class CiclosPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  ciclos = signal<Ciclo[]>([]);
  plantillas = signal<Plantilla[]>([]);
  abierto = signal(false);
  nombre = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  inicio = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  cierre = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  form = new FormGroup({
    nombre: this.nombre,
    fecha_inicio: this.inicio,
    fecha_cierre: this.cierre,
    plantilla_default: new FormControl<number | null>(null, { validators: [Validators.required] }),
    criterios_generales: new FormControl('', { nonNullable: true }),
    areas: new FormControl<number[]>([], { nonNullable: true }),
  });

  constructor() {
    this.cargar();
    this.http.get<Pagina<Plantilla>>(`${API}/plantillas/`).subscribe((p) => this.plantillas.set(p.results));
  }

  cargar(): void {
    this.http.get<Pagina<Ciclo>>(`${API}/ciclos/`).subscribe((p) => this.ciclos.set(p.results));
  }

  nuevo(): void {
    this.abierto.set(true);
  }

  guardar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    this.http.post(`${API}/ciclos/`, { ...raw, plantilla_default: Number(raw.plantilla_default) }).subscribe({
      next: () => {
        this.alertas.success('Ciclo creado.');
        this.abierto.set(false);
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}

@Component({
  selector: 'app-ciclo-detalle',
  imports: [ButtonComponent, BadgeComponent, ModalComponent, InputDateComponent, ReactiveFormsModule],
  template: `
    @if (ciclo(); as actual) {
      <h1 class="text-2xl font-semibold">{{ actual.nombre }}</h1>
      <p class="mt-2 text-sm text-slate-600">
        <app-badge [label]="actual.estado" />
        {{ actual.fecha_inicio }} → {{ actual.fecha_cierre }} · {{ actual.total_evals || 0 }} evaluaciones
        · {{ actual.sin_evaluador_count || 0 }} sin evaluador
      </p>
      <div class="mt-4 flex flex-wrap gap-2">
        <app-button size="sm" label="Activar" (buttonClick)="pedir('activar')" />
        <app-button size="sm" color="secondary" label="Pausar" (buttonClick)="pedir('pausar')" />
        <app-button size="sm" color="danger" label="Cancelar" (buttonClick)="pedir('cancelar')" />
        <app-button size="sm" color="light" label="Reprogramar" (buttonClick)="reprogramar.set(true)" />
      </div>
      @if (reprogramar()) {
        <form class="mt-4 flex max-w-md items-end gap-3" (ngSubmit)="guardarFechas()">
          <app-input-date label="Inicio" [control]="inicio" />
          <app-input-date label="Cierre" [control]="cierre" />
          <app-button type="submit" label="Guardar fechas" />
        </form>
      }
      <ul class="mt-6 divide-y rounded-xl border border-slate-200 bg-white">
        @for (ev of participantes(); track ev.id) {
          <li class="flex items-center justify-between px-4 py-3 text-sm">
            <span>{{ ev.evaluado?.nombre }} · {{ ev.puesto_nombre }}</span>
            <span class="text-slate-500">{{ ev.estado_display }}{{ ev.sin_evaluador ? ' · sin evaluador' : '' }}</span>
          </li>
        }
      </ul>
      <app-modal [open]="!!accion()" title="Confirmar" (confirm)="confirmar()" (cancel)="accion.set(null)">
        ¿Confirmás {{ accion() }} este ciclo?
      </app-modal>
    }
  `,
})
export class CicloDetallePage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly alertas = inject(AlertService);
  ciclo = signal<Ciclo | null>(null);
  participantes = signal<{ id: number; evaluado?: { nombre: string }; puesto_nombre: string; estado_display: string; sin_evaluador: boolean }[]>([]);
  accion = signal<string | null>(null);
  reprogramar = signal(false);
  inicio = new FormControl('', { nonNullable: true });
  cierre = new FormControl('', { nonNullable: true });

  constructor() {
    const id = this.route.snapshot.paramMap.get('id');
    this.http.get<Ciclo>(`${API}/ciclos/${id}/`).subscribe((ciclo) => {
      this.ciclo.set(ciclo);
      this.inicio.setValue(ciclo.fecha_inicio);
      this.cierre.setValue(ciclo.fecha_cierre);
    });
    this.http
      .get<{ id: number; evaluado?: { nombre: string }; puesto_nombre: string; estado_display: string; sin_evaluador: boolean }[]>(
        `${API}/ciclos/${id}/participantes/`,
      )
      .subscribe((lista) => this.participantes.set(lista));
  }

  pedir(accion: string): void {
    this.accion.set(accion);
  }

  confirmar(): void {
    const ciclo = this.ciclo();
    const accion = this.accion();
    if (!ciclo || !accion) return;
    this.http.post<Ciclo>(`${API}/ciclos/${ciclo.id}/${accion}/`, {}).subscribe({
      next: (actualizado) => {
        this.ciclo.set(actualizado);
        this.accion.set(null);
        this.alertas.success('Ciclo actualizado.');
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  guardarFechas(): void {
    const ciclo = this.ciclo();
    if (!ciclo) return;
    this.http
      .post<Ciclo>(`${API}/ciclos/${ciclo.id}/reprogramar/`, {
        fecha_inicio: this.inicio.value,
        fecha_cierre: this.cierre.value,
      })
      .subscribe({
        next: (actualizado) => {
          this.ciclo.set(actualizado);
          this.reprogramar.set(false);
          this.alertas.success('Fechas actualizadas.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }
}
