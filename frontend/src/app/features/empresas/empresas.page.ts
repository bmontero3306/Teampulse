import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';
import { TenantService } from '../../core/tenant.service';
import { AlertService } from '../../shared/alert.service';
import { BadgeComponent } from '../../shared/badge.component';
import { ButtonComponent } from '../../shared/button.component';
import { mensajeError } from '../../shared/errores';
import { InputTextComponent } from '../../shared/input-text.component';
import { ModalComponent } from '../../shared/modal.component';

interface Empresa {
  id: number;
  nombre: string;
  razon_social: string;
  cuit: string;
  email_contacto: string;
  telefono: string;
  direccion: string;
  estado: string;
}

@Component({
  selector: 'app-empresas',
  imports: [ReactiveFormsModule, ButtonComponent, InputTextComponent, BadgeComponent, ModalComponent],
  template: `
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Empresas</h1>
      <app-button label="Nueva empresa" (buttonClick)="nueva()" />
    </div>
    <ul class="mt-6 divide-y rounded-xl border border-slate-200 bg-white">
      @for (empresa of empresas(); track empresa.id) {
        <li class="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
          <div>
            <p class="font-medium">{{ empresa.nombre }}</p>
            <p class="text-slate-500">{{ empresa.cuit }} · {{ empresa.email_contacto }}</p>
          </div>
          <div class="flex items-center gap-2">
            <app-badge [label]="empresa.estado" [tono]="empresa.estado === 'activa' ? 'ok' : 'warn'" />
            <button type="button" class="text-sky-700" (click)="usar(empresa)">Usar</button>
            <button type="button" class="text-slate-600" (click)="editar(empresa)">Editar</button>
            @if (empresa.estado === 'activa') {
              <button type="button" class="text-rose-700" (click)="pedir('suspender', empresa)">Suspender</button>
            } @else {
              <button type="button" class="text-emerald-700" (click)="pedir('activar', empresa)">Activar</button>
            }
          </div>
        </li>
      }
    </ul>

    @if (formulario()) {
      <form class="mt-6 max-w-xl space-y-3 rounded-xl border border-slate-200 bg-white p-4" [formGroup]="form" (ngSubmit)="guardar()">
        <h2 class="font-semibold">{{ editando() ? 'Editar empresa' : 'Nueva empresa' }}</h2>
        <app-input-text label="Nombre" [control]="ctrl('nombre')" />
        <app-input-text label="Razón social" [control]="ctrl('razon_social')" />
        <app-input-text label="CUIT" [control]="ctrl('cuit')" help="11 dígitos, con o sin guiones." />
        <app-input-text label="Email" type="email" [control]="ctrl('email_contacto')" />
        <app-input-text label="Teléfono" [control]="ctrl('telefono')" />
        <app-input-text label="Dirección" [control]="ctrl('direccion')" />
        <app-button type="submit" label="Guardar" />
      </form>
    }

    <app-modal [open]="!!accion()" [title]="accion() === 'suspender' ? 'Suspender empresa' : 'Activar empresa'" (confirm)="confirmar()" (cancel)="accion.set(null)">
      {{ objetivo()?.nombre }}
    </app-modal>
  `,
})
export class EmpresasPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  private readonly tenant = inject(TenantService);
  empresas = signal<Empresa[]>([]);
  formulario = signal(false);
  editando = signal<number | null>(null);
  accion = signal<'suspender' | 'activar' | null>(null);
  objetivo = signal<Empresa | null>(null);
  form = new FormGroup({
    nombre: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    razon_social: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    cuit: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    email_contacto: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    telefono: new FormControl('', { nonNullable: true }),
    direccion: new FormControl('', { nonNullable: true }),
    estado: new FormControl('activa', { nonNullable: true }),
  });

  constructor() {
    this.cargar();
  }

  ctrl(nombre: keyof typeof this.form.controls): FormControl {
    return this.form.controls[nombre];
  }

  cargar(): void {
    this.http.get<Pagina<Empresa>>(`${API}/empresas/`).subscribe((pagina) => this.empresas.set(pagina.results));
  }

  nueva(): void {
    this.editando.set(null);
    this.form.reset({ estado: 'activa' });
    this.formulario.set(true);
  }

  editar(empresa: Empresa): void {
    this.editando.set(empresa.id);
    this.form.patchValue(empresa);
    this.formulario.set(true);
  }

  guardar(): void {
    const id = this.editando();
    const req = id
      ? this.http.patch(`${API}/empresas/${id}/`, this.form.getRawValue())
      : this.http.post(`${API}/empresas/`, this.form.getRawValue());
    req.subscribe({
      next: () => {
        this.alertas.success('Empresa guardada.');
        this.formulario.set(false);
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  usar(empresa: Empresa): void {
    this.tenant.setEmpresa(empresa.id);
    this.alertas.success(`Trabajando en ${empresa.nombre}.`);
  }

  pedir(accion: 'suspender' | 'activar', empresa: Empresa): void {
    this.accion.set(accion);
    this.objetivo.set(empresa);
  }

  confirmar(): void {
    const empresa = this.objetivo();
    const accion = this.accion();
    if (!empresa || !accion) return;
    this.http.post(`${API}/empresas/${empresa.id}/${accion}/`, {}).subscribe({
      next: () => {
        this.alertas.success('Estado actualizado.');
        this.accion.set(null);
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}
