import { HttpClient } from '@angular/common/http';
import { Component, inject, input, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';
import { AlertService } from '../../shared/alert.service';
import { ButtonComponent } from '../../shared/button.component';
import { mensajeError } from '../../shared/errores';
import { InputTextComponent } from '../../shared/input-text.component';

interface Nodo {
  id: number;
  nombre: string;
  area: string | null;
  hijos: Nodo[];
}

@Component({
  selector: 'app-nodo-org',
  imports: [NodoOrgComponent],
  template: `
    <div class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
      <p class="font-medium">{{ nodo().nombre }}</p>
      @if (nodo().area) { <p class="text-xs text-slate-500">{{ nodo().area }}</p> }
      @if (nodo().hijos.length) {
        <div class="mt-2 space-y-2 border-l border-slate-200 pl-3">
          @for (hijo of nodo().hijos; track hijo.id) {
            <app-nodo-org [nodo]="hijo" />
          }
        </div>
      }
    </div>
  `,
})
export class NodoOrgComponent {
  nodo = input.required<Nodo>();
}

@Component({
  selector: 'app-organizacion',
  imports: [ReactiveFormsModule, ButtonComponent, InputTextComponent, NodoOrgComponent],
  template: `
    <h1 class="text-2xl font-semibold">Organización</h1>
    <div class="mt-4 flex gap-2 text-sm">
      @for (tab of tabs; track tab.id) {
        <button type="button" class="rounded-lg px-3 py-1.5" [class.bg-sky-50]="seccion() === tab.id" [class.text-sky-800]="seccion() === tab.id" (click)="ir(tab.id)">
          {{ tab.label }}
        </button>
      }
    </div>
    @if (seccion() === 'organigrama') {
      <div class="mt-6 space-y-2">
        @for (nodo of raices(); track nodo.id) {
          <app-nodo-org [nodo]="nodo" />
        } @empty {
          <p class="text-sm text-slate-500">No hay puestos para mostrar.</p>
        }
      </div>
    } @else {
      <form class="mt-6 max-w-lg space-y-3" [formGroup]="form" (ngSubmit)="guardar()">
        <app-input-text label="Nombre" [control]="nombre" />
        @if (seccion() === 'competencias') {
          <label class="block text-sm">Tipo
            <select formControlName="tipo" class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
              <option value="tecnica">Técnica</option>
              <option value="actitudinal">Actitudinal</option>
              <option value="objetivo">Objetivo</option>
              <option value="otra">Otra</option>
            </select>
          </label>
        }
        <app-button type="submit" [label]="editando() ? 'Guardar cambios' : 'Crear'" />
      </form>
      <ul class="mt-6 divide-y rounded-xl border border-slate-200 bg-white">
        @for (item of items(); track item.id) {
          <li class="flex items-center justify-between px-4 py-3 text-sm">
            <span>{{ item.nombre }}</span>
            <span class="flex gap-3">
              <button type="button" class="text-sky-700" (click)="elegir(item)">Editar</button>
              <button type="button" class="text-rose-700" (click)="baja(item)">Desactivar</button>
            </span>
          </li>
        }
      </ul>
    }
  `,
})
export class OrganizacionPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  tabs = [
    { id: 'organigrama', label: 'Organigrama' },
    { id: 'areas', label: 'Áreas' },
    { id: 'puestos', label: 'Puestos' },
    { id: 'competencias', label: 'Competencias' },
  ];
  seccion = signal('organigrama');
  raices = signal<Nodo[]>([]);
  items = signal<{ id: number; nombre: string }[]>([]);
  editando = signal<number | null>(null);
  nombre = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  form = new FormGroup({
    nombre: this.nombre,
    tipo: new FormControl('tecnica', { nonNullable: true }),
    descripcion: new FormControl('', { nonNullable: true }),
  });

  constructor() {
    this.cargarOrganigrama();
  }

  ir(id: string): void {
    this.seccion.set(id);
    this.editando.set(null);
    if (id === 'organigrama') this.cargarOrganigrama();
    else this.cargarLista();
  }

  cargarOrganigrama(): void {
    this.http.get<{ raices: Nodo[] }>(`${API}/organigrama/`).subscribe((data) => this.raices.set(data.raices));
  }

  cargarLista(): void {
    this.http
      .get<Pagina<{ id: number; nombre: string }>>(`${API}/${this.seccion()}/`)
      .subscribe((pagina) => this.items.set(pagina.results));
  }

  elegir(item: { id: number; nombre: string }): void {
    this.editando.set(item.id);
    this.nombre.setValue(item.nombre);
  }

  guardar(): void {
    const id = this.editando();
    const body = this.form.getRawValue();
    const req = id
      ? this.http.patch(`${API}/${this.seccion()}/${id}/`, body)
      : this.http.post(`${API}/${this.seccion()}/`, body);
    req.subscribe({
      next: () => {
        this.alertas.success('Guardado.');
        this.editando.set(null);
        this.nombre.setValue('');
        this.cargarLista();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  baja(item: { id: number }): void {
    this.http.delete(`${API}/${this.seccion()}/${item.id}/`).subscribe({
      next: () => this.cargarLista(),
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}
