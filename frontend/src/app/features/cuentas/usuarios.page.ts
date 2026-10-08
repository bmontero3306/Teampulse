import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { API } from '../../core/api';
import { Pagina, Usuario } from '../../core/models';
import { AlertService } from '../../shared/alert.service';
import { ButtonComponent } from '../../shared/button.component';
import { DynamicTableComponent } from '../../shared/dynamic-table.component';
import { mensajeError } from '../../shared/errores';
import { InputTextComponent } from '../../shared/input-text.component';
import { ModalComponent } from '../../shared/modal.component';

@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule, ButtonComponent, InputTextComponent, DynamicTableComponent, ModalComponent],
  template: `
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Usuarios</h1>
      <app-button label="Nuevo usuario" (buttonClick)="nuevo()" />
    </div>
    <div class="mt-4">
      <app-dynamic-table
        [columns]="columnas"
        [rows]="filas()"
        [showOptions]="true"
        (rowClick)="editar($event)"
      />
    </div>
    @if (formulario()) {
      <form class="mt-6 max-w-xl space-y-3 rounded-xl border border-slate-200 bg-white p-4" [formGroup]="form" (ngSubmit)="guardar()">
        <h2 class="font-semibold">{{ editando() ? 'Editar usuario' : 'Nuevo usuario' }}</h2>
        <app-input-text label="Nombre" [control]="ctrl('first_name')" />
        <app-input-text label="Apellido" [control]="ctrl('last_name')" />
        <app-input-text label="Correo" type="email" [control]="ctrl('email')" />
        <app-input-text label="DNI" [control]="ctrl('dni')" />
        <label class="block text-sm">Rol
          <select formControlName="rol" class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
            <option value="empleado">Empleado</option>
            <option value="supervisor">Supervisor</option>
            <option value="admin_rrhh">Admin RRHH</option>
          </select>
        </label>
        @if (clave()) { <p class="text-sm text-emerald-800">Contraseña temporal: {{ clave() }}</p> }
        <app-button type="submit" label="Guardar" />
      </form>
    }
    @if (seleccionado(); as usuario) {
      <div class="mt-4 flex gap-2">
        <app-button color="danger" size="sm" label="Desactivar" (buttonClick)="pedir('desactivar')" />
        <app-button color="warning" size="sm" label="Bloquear" (buttonClick)="pedir('bloquear')" />
        <app-button color="secondary" size="sm" label="Reset clave" (buttonClick)="pedir('reset-clave')" />
      </div>
    }
    <app-modal [open]="!!accion()" [title]="'Confirmar'" (confirm)="confirmar()" (cancel)="accion.set(null)">
      ¿Confirmás la acción sobre {{ seleccionado()?.email }}?
    </app-modal>
  `,
})
export class UsuariosPage {
  private readonly http = inject(HttpClient);
  private readonly alertas = inject(AlertService);
  columnas = [
    { field: 'nombre', header: 'Nombre' },
    { field: 'email', header: 'Correo' },
    { field: 'rol_display', header: 'Rol' },
    { field: 'area_nombre', header: 'Área' },
  ];
  usuarios = signal<Usuario[]>([]);
  formulario = signal(false);
  editando = signal<number | null>(null);
  seleccionado = signal<Usuario | null>(null);
  accion = signal<string | null>(null);
  clave = signal('');
  form = new FormGroup({
    first_name: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    last_name: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    dni: new FormControl('', { nonNullable: true }),
    rol: new FormControl('empleado', { nonNullable: true }),
  });

  constructor() {
    this.cargar();
  }

  filas(): Record<string, unknown>[] {
    return this.usuarios() as unknown as Record<string, unknown>[];
  }

  ctrl(nombre: 'first_name' | 'last_name' | 'email' | 'dni'): FormControl {
    return this.form.controls[nombre];
  }

  cargar(): void {
    this.http.get<Pagina<Usuario>>(`${API}/usuarios/`).subscribe((pagina) => this.usuarios.set(pagina.results));
  }

  nuevo(): void {
    this.editando.set(null);
    this.clave.set('');
    this.form.reset({ rol: 'empleado' });
    this.formulario.set(true);
  }

  editar(row: Record<string, unknown>): void {
    const usuario = row as unknown as Usuario;
    this.seleccionado.set(usuario);
    this.editando.set(usuario.id);
    this.form.patchValue({
      first_name: usuario.first_name,
      last_name: usuario.last_name,
      email: usuario.email,
      dni: usuario.dni ?? '',
      rol: usuario.rol,
    });
    this.formulario.set(true);
  }

  guardar(): void {
    const id = this.editando();
    const req = id
      ? this.http.patch<Usuario & { clave_temporal?: string }>(`${API}/usuarios/${id}/`, this.form.getRawValue())
      : this.http.post<Usuario & { clave_temporal?: string }>(`${API}/usuarios/`, this.form.getRawValue());
    req.subscribe({
      next: (usuario) => {
        this.clave.set(usuario.clave_temporal ?? '');
        this.alertas.success('Usuario guardado.');
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  pedir(accion: string): void {
    this.accion.set(accion);
  }

  confirmar(): void {
    const usuario = this.seleccionado();
    const accion = this.accion();
    if (!usuario || !accion) return;
    this.http.post<Usuario & { clave_temporal?: string }>(`${API}/usuarios/${usuario.id}/${accion}/`, {}).subscribe({
      next: (resp) => {
        if (resp.clave_temporal) this.clave.set(resp.clave_temporal);
        this.alertas.success('Acción aplicada.');
        this.accion.set(null);
        this.cargar();
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }
}
