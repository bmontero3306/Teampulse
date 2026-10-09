import { Component, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { TenantService } from '../../core/tenant.service';
import { AlertService } from '../../shared/alert.service';
import { EmpresaApi } from './empresa.api';
import { Empresa } from './empresa.model';

/** Markup de _selector_empresa.html. No está importado por el shell. */
@Component({
  selector: 'app-selector-empresa',
  template: `
    @if (auth.sesion()?.usuario?.rol === 'superadmin') {
      <form class="mt-0.5 max-w-xs" id="form-selector-empresa" (submit)="$event.preventDefault()">
        <input type="hidden" name="next" [value]="ruta()" />
        <label for="selector-empresa" class="sr-only">Seleccionar empresa</label>
        <select
          id="selector-empresa"
          class="block w-full truncate rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          [value]="seleccionada()"
          (change)="elegir($event)"
        >
          <option value="" disabled>Elegí una empresa</option>
          @for (emp of empresas(); track emp.id) {
            <option [value]="emp.id">{{ emp.nombre }}</option>
          }
        </select>
      </form>
    }
  `,
})
export class SelectorEmpresaComponent {
  readonly auth = inject(AuthService);
  private readonly tenant = inject(TenantService);
  private readonly alertas = inject(AlertService);
  private readonly api = inject(EmpresaApi);
  private readonly router = inject(Router);
  private cargado = false;
  empresas = signal<Empresa[]>([]);

  constructor() {
    effect(() => {
      const rol = this.auth.sesion()?.usuario?.rol;
      if (rol !== 'superadmin' || this.cargado) {
        return;
      }
      this.cargado = true;
      this.api.listar().subscribe((lista) => this.empresas.set(lista));
    });
  }

  seleccionada(): string {
    const id = this.auth.sesion()?.empresa_actual?.id ?? this.tenant.empresaId();
    return id == null ? '' : String(id);
  }

  ruta(): string {
    return this.router.url.split('?')[0] ?? '';
  }

  elegir(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    if (!value) {
      return;
    }
    const id = Number(value);
    const empresa = this.empresas().find((item) => item.id === id);
    this.tenant.setEmpresa(id);
    this.auth.loadMe().subscribe(() => {
      if (empresa) {
        this.alertas.success(`Contexto cambiado a ${empresa.nombre}.`);
      }
    });
  }
}
