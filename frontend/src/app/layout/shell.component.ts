import { HttpClient } from '@angular/common/http';
import { AfterViewChecked, Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { API } from '../core/api';
import { AuthService } from '../core/auth.service';
import { Pagina } from '../core/models';
import { TenantService } from '../core/tenant.service';
import { AlertComponent } from '../shared/alert.component';

declare const lucide: { createIcons: () => void } | undefined;

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AlertComponent],
  template: `
    <div class="flex min-h-screen">
      <aside class="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <a routerLink="/dashboard" class="flex h-16 items-center px-4 text-lg font-semibold text-sky-700">
          TeamPulse
        </a>
        <nav class="flex-1 space-y-1 overflow-y-auto p-3 text-sm">
          @for (item of auth.sesion()?.nav ?? []; track item.clave) {
            <a
              [routerLink]="item.href"
              routerLinkActive="bg-sky-50 text-sky-800"
              class="flex items-center gap-3 rounded-lg px-2 py-2 font-medium text-slate-700 hover:bg-sky-50"
            >
              <i [attr.data-lucide]="item.icono" class="h-[18px] w-[18px]"></i>
              {{ item.etiqueta }}
            </a>
          }
        </nav>
      </aside>
      <div class="flex min-w-0 flex-1 flex-col">
        <header class="sticky top-0 z-20 flex min-h-16 items-center gap-3 border-b border-slate-200 bg-white px-6">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-slate-800">
              {{ auth.sesion()?.empresa_actual?.nombre || 'Sin empresa' }}
            </p>
            @if (auth.sesion()?.usuario?.rol === 'superadmin') {
              <select
                class="mt-1 max-w-xs rounded-lg border border-slate-300 px-2 py-1 text-sm"
                [value]="tenant.empresaId() ?? ''"
                (change)="cambiarEmpresa($event)"
              >
                <option value="">Elegí una empresa</option>
                @for (empresa of empresas; track empresa.id) {
                  <option [value]="empresa.id">{{ empresa.nombre }}</option>
                }
              </select>
            }
          </div>
          <a routerLink="/notificaciones" class="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100">
            <i data-lucide="bell" class="h-5 w-5"></i>
            @if ((auth.sesion()?.notificaciones_no_leidas ?? 0) > 0) {
              <span class="absolute right-1 top-1 h-2 w-2 rounded-full bg-rose-500"></span>
            }
          </a>
          <div class="text-right text-sm">
            <p class="font-medium text-slate-800">{{ auth.sesion()?.usuario?.nombre }}</p>
            <p class="text-xs text-slate-500">{{ auth.sesion()?.usuario?.rol_display }}</p>
          </div>
          <button type="button" class="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100" (click)="salir()">
            Salir
          </button>
        </header>
        <main class="flex-1 p-6">
          <router-outlet />
        </main>
      </div>
    </div>
    <app-alert />
  `,
})
export class ShellComponent implements AfterViewChecked {
  readonly auth = inject(AuthService);
  readonly tenant = inject(TenantService);
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);
  empresas: { id: number; nombre: string; estado: string }[] = [];

  constructor() {
    this.auth.loadMe().subscribe((sesion) => {
      if (sesion?.usuario.rol === 'superadmin') {
        this.cargarEmpresas();
      }
    });
  }

  ngAfterViewChecked(): void {
    lucide?.createIcons();
  }

  cambiarEmpresa(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.tenant.setEmpresa(value ? Number(value) : null);
    this.auth.loadMe().subscribe(() => this.router.navigateByUrl('/dashboard'));
  }

  salir(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/']),
      error: () => this.router.navigate(['/']),
    });
  }

  private cargarEmpresas(): void {
    this.http.get<Pagina<{ id: number; nombre: string; estado: string }>>(`${API}/empresas/`).subscribe({
      next: (pagina) => (this.empresas = pagina.results),
    });
  }
}
