import { Component, OnInit, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ESTADOS_EMPRESA, Empresa, EmpresaPayload, ErroresEmpresa, ERRORES_VACIOS } from './empresa.model';

@Component({
  selector: 'app-empresa-form',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <section class="mx-auto max-w-3xl">
      <div class="mb-6">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ titulo() }}</h1>
        <p class="mt-1 text-sm text-slate-600">
          @if (esFicha()) {
            Podés actualizar el nombre y los datos de contacto de tu empresa.
          } @else {
            Completá los datos de la empresa. El CUIT no puede repetirse.
          }
        </p>
      </div>

      <form class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6" [formGroup]="form" (ngSubmit)="enviar()">
        @if (errores().generales.length) {
          <ul class="mb-4 space-y-1 text-sm text-red-700">
            @for (error of errores().generales; track $index) {
              <li>{{ error }}</li>
            }
          </ul>
        }

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label for="id_nombre" class="mb-1 block text-sm font-medium text-slate-700">
              Nombre <span class="text-red-600">*</span>
            </label>
            <input
              id="id_nombre"
              type="text"
              formControlName="nombre"
              maxlength="200"
              required
              class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            @for (error of mensajes('nombre'); track $index) {
              <p class="mt-1 text-sm text-red-600">{{ error }}</p>
            }
          </div>

          @if (!esFicha()) {
            <div>
              <label for="id_razon_social" class="mb-1 block text-sm font-medium text-slate-700">
                Razón social <span class="text-red-600">*</span>
              </label>
              <input
                id="id_razon_social"
                type="text"
                formControlName="razon_social"
                maxlength="200"
                required
                class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
              @for (error of mensajes('razon_social'); track $index) {
                <p class="mt-1 text-sm text-red-600">{{ error }}</p>
              }
            </div>

            <div>
              <label for="id_cuit" class="mb-1 block text-sm font-medium text-slate-700">
                CUIT <span class="text-red-600">*</span>
              </label>
              <input
                id="id_cuit"
                type="text"
                formControlName="cuit"
                maxlength="20"
                required
                placeholder="30-12345678-9"
                autocomplete="off"
                class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
              <p class="mt-1 text-xs text-slate-500">11 dígitos, con o sin guiones (por ejemplo 30-12345678-9).</p>
              @for (error of mensajes('cuit'); track $index) {
                <p class="mt-1 text-sm text-red-600">{{ error }}</p>
              }
            </div>
          }

          <div>
            <label for="id_email_contacto" class="mb-1 block text-sm font-medium text-slate-700">
              Email de contacto <span class="text-red-600">*</span>
            </label>
            <input
              id="id_email_contacto"
              type="email"
              formControlName="email_contacto"
              required
              class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            @for (error of mensajes('email_contacto'); track $index) {
              <p class="mt-1 text-sm text-red-600">{{ error }}</p>
            }
          </div>

          <div>
            <label for="id_telefono" class="mb-1 block text-sm font-medium text-slate-700">Teléfono</label>
            <input
              id="id_telefono"
              type="text"
              formControlName="telefono"
              maxlength="50"
              class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            @for (error of mensajes('telefono'); track $index) {
              <p class="mt-1 text-sm text-red-600">{{ error }}</p>
            }
          </div>

          <div class="sm:col-span-2">
            <label for="id_direccion" class="mb-1 block text-sm font-medium text-slate-700">Dirección</label>
            <input
              id="id_direccion"
              type="text"
              formControlName="direccion"
              maxlength="255"
              class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            @for (error of mensajes('direccion'); track $index) {
              <p class="mt-1 text-sm text-red-600">{{ error }}</p>
            }
          </div>

          @if (!esFicha()) {
            <div>
              <label for="id_estado" class="mb-1 block text-sm font-medium text-slate-700">
                Estado <span class="text-red-600">*</span>
              </label>
              <select
                id="id_estado"
                formControlName="estado"
                required
                class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              >
                @for (opcion of estados; track opcion.value) {
                  <option [value]="opcion.value">{{ opcion.label }}</option>
                }
              </select>
              @for (error of mensajes('estado'); track $index) {
                <p class="mt-1 text-sm text-red-600">{{ error }}</p>
              }
            </div>
          }
        </div>

        <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          @if (empresa(); as actual) {
            <a
              [routerLink]="['/empresas', actual.id]"
              class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </a>
          } @else {
            <a
              routerLink="/empresas"
              class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </a>
          }
          <button
            type="submit"
            class="inline-flex items-center justify-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-700"
          >
            Guardar
          </button>
        </div>
      </form>
    </section>
  `,
})
export class EmpresaFormComponent implements OnInit {
  readonly estados = ESTADOS_EMPRESA;
  titulo = input('Nueva empresa');
  esFicha = input(false);
  empresa = input<Empresa | null>(null);
  errores = input<ErroresEmpresa>(ERRORES_VACIOS);
  guardar = output<EmpresaPayload>();

  readonly form = new FormGroup({
    nombre: new FormControl('', { nonNullable: true }),
    razon_social: new FormControl('', { nonNullable: true }),
    cuit: new FormControl('', { nonNullable: true }),
    email_contacto: new FormControl('', { nonNullable: true }),
    telefono: new FormControl('', { nonNullable: true }),
    direccion: new FormControl('', { nonNullable: true }),
    estado: new FormControl('activa', { nonNullable: true }),
  });

  ngOnInit(): void {
    const empresa = this.empresa();
    this.form.reset({
      nombre: empresa?.nombre ?? '',
      razon_social: empresa?.razon_social ?? '',
      cuit: empresa?.cuit ?? '',
      email_contacto: empresa?.email_contacto ?? '',
      telefono: empresa?.telefono ?? '',
      direccion: empresa?.direccion ?? '',
      estado: empresa?.estado || 'activa',
    });
  }

  mensajes(campo: string): string[] {
    return this.errores().campos[campo] ?? [];
  }

  enviar(): void {
    this.guardar.emit(this.form.getRawValue());
  }
}
