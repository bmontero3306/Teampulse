import { HttpClient } from '@angular/common/http';
import { AfterViewChecked, Component, HostListener, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink, RouterOutlet } from '@angular/router';

import { API } from '../core/api';
import { AuthService } from '../core/auth.service';
import { Pagina } from '../core/models';
import { TenantService } from '../core/tenant.service';
import { AlertService } from '../shared/alert.service';

declare const lucide: { createIcons: (opts?: { attrs?: Record<string, string> }) => void } | undefined;

/** Equivale a theme/templates/app_shell.html. */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink],
  template: `
    <div id="app-shell" class="flex min-h-screen overflow-x-hidden">
      <div
        id="sidebar-backdrop"
        class="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
        [class.hidden]="!menuAbierto()"
        (click)="cerrarMovil()"
      ></div>

      <aside
        id="sidebar"
        class="group/nav fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-[width,transform] duration-200 lg:static lg:translate-x-0 lg:w-64 data-[colapsado=true]:lg:w-16"
        [class.-translate-x-full]="!menuAbierto()"
        [class.translate-x-0]="menuAbierto()"
        [attr.data-colapsado]="colapsado() ? 'true' : 'false'"
        aria-label="Menú principal"
      >
        <div class="flex h-16 items-center gap-2 border-b border-slate-200 px-3">
          <a routerLink="/dashboard" class="flex min-w-0 items-center gap-2 text-lg font-semibold tracking-tight text-sky-700" (click)="cerrarMovil()">
            <img src="logo_solo.png" alt="TeamPulse" class="h-9 w-9 shrink-0 rounded-lg object-contain">
            <span class="truncate group-data-[colapsado=true]/nav:lg:hidden">TeamPulse</span>
          </a>
        </div>
        <nav class="flex-1 space-y-1 overflow-y-auto overflow-x-hidden p-3 text-sm" aria-label="Secciones">
          @if (auth.sesion(); as sesion) {
            @for (item of sesion.nav; track item.clave) {
              <a
                [routerLink]="item.href"
                [attr.data-nav]="item.clave"
                [attr.title]="item.etiqueta"
                [class]="clasesNav(item.href)"
                (click)="cerrarMovil()"
              >
                <span class="flex h-8 w-8 shrink-0 items-center justify-center" aria-hidden="true">
                  <i [attr.data-lucide]="item.icono || 'circle'" class="h-[18px] w-[18px]"></i>
                </span>
                <span class="truncate group-data-[colapsado=true]/nav:lg:hidden">{{ item.etiqueta }}</span>
              </a>
            } @empty {
              <a routerLink="/dashboard" data-nav="dashboard" class="flex items-center gap-3 rounded-lg px-2 py-2 font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-800" (click)="cerrarMovil()">
                <span class="flex h-8 w-8 shrink-0 items-center justify-center" aria-hidden="true">
                  <i data-lucide="layout-dashboard" class="h-[18px] w-[18px]"></i>
                </span>
                <span class="truncate group-data-[colapsado=true]/nav:lg:hidden">Panel</span>
              </a>
            }
          }
        </nav>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col">
        <header class="sticky top-0 z-20 flex min-h-16 flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 sm:px-6">
          <button
            type="button"
            id="btn-menu-movil"
            class="inline-flex rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Abrir menú"
            aria-controls="sidebar"
            [attr.aria-expanded]="menuAbierto()"
            (click)="toggleMovil()"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <button
            type="button"
            id="btn-colapsar-sidebar"
            class="hidden rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:inline-flex"
            [attr.aria-label]="colapsado() ? 'Expandir menú' : 'Colapsar menú'"
            (click)="toggleColapsado()"
          >
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            </svg>
          </button>

          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-slate-800">
              @if (auth.sesion(); as sesion) {
                {{ sesion.empresa_actual?.nombre || 'Sin empresa' }}
              }
            </p>
            @if (auth.sesion()?.usuario?.rol === 'superadmin') {
              <form class="mt-0.5 max-w-xs" id="form-selector-empresa" (submit)="$event.preventDefault()">
                <label for="selector-empresa" class="sr-only">Seleccionar empresa</label>
                <select
                  id="selector-empresa"
                  class="block w-full truncate rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  [value]="empresaSeleccionada()"
                  (change)="cambiarEmpresa($event)"
                >
                  <option value="" disabled>Elegí una empresa</option>
                  @for (empresa of empresas; track empresa.id) {
                    <option [value]="empresa.id">{{ empresa.nombre }}</option>
                  }
                </select>
              </form>
            }
          </div>

          @if (auth.sesion(); as sesion) {
            <a routerLink="/notificaciones" class="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label="Notificaciones">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
              </svg>
              @if (sesion.notificaciones_no_leidas) {
                <span class="absolute -top-0.5 -right-0.5 inline-flex min-w-4 items-center justify-center rounded-full bg-sky-600 px-1 text-[10px] font-semibold text-white">
                  {{ sesion.notificaciones_no_leidas }}
                </span>
              }
            </a>

            <div class="min-w-0 max-w-40 text-right text-sm sm:max-w-none">
              <p class="truncate font-medium text-slate-800">
                {{ sesion.usuario.nombre || sesion.usuario.email }}
              </p>
              <p class="truncate text-xs text-slate-500">
                {{ sesion.usuario.rol_display }}
              </p>
            </div>

            <form (submit)="$event.preventDefault(); salir()">
              <button type="submit" class="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900">
                Salir
              </button>
            </form>
          }
        </header>

        <main class="w-full min-w-0 flex-1 px-4 py-6 sm:px-6">
          @if (alertas.alertas().length) {
            <ul class="mb-4 space-y-2">
              @for (message of alertas.alertas(); track message.id) {
                <li [class]="clasesMensaje(message.tipo)">{{ message.texto }}</li>
              }
            </ul>
          }
          <router-outlet />
        </main>
      </div>
    </div>
  `,
})
export class ShellComponent implements AfterViewChecked {
  readonly auth = inject(AuthService);
  readonly tenant = inject(TenantService);
  readonly alertas = inject(AlertService);
  private readonly title = inject(Title);
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);

  readonly menuAbierto = signal(false);
  readonly colapsado = signal(false);
  empresas: { id: number; nombre: string; estado: string }[] = [];

  constructor() {
    this.title.setTitle('TeamPulse · TeamPulse');
    this.auth.loadMe().subscribe((sesion) => {
      if (sesion?.usuario.rol === 'superadmin') {
        this.cargarEmpresas();
      }
    });
  }

  ngAfterViewChecked(): void {
    lucide?.createIcons({ attrs: { 'stroke-width': '1.8' } });
  }

  @HostListener('document:keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.cerrarMovil();
    }
  }

  toggleMovil(): void {
    if (this.menuAbierto()) {
      this.cerrarMovil();
    } else {
      this.abrirMovil();
    }
  }

  abrirMovil(): void {
    this.menuAbierto.set(true);
  }

  cerrarMovil(): void {
    this.menuAbierto.set(false);
  }

  toggleColapsado(): void {
    this.colapsado.update((valor) => !valor);
  }

  clasesNav(href: string): string {
    const base = 'flex items-center gap-3 rounded-lg px-2 py-2 font-medium hover:bg-sky-50 hover:text-sky-800';
    const path = this.router.url.split('?')[0].split('#')[0];
    const activo = path === href || (href !== '/' && path.includes(href));
    return activo ? `${base} bg-sky-50 text-sky-800` : `${base} text-slate-700`;
  }

  clasesMensaje(tipo: string): string {
    const base = 'rounded-lg border px-4 py-3 text-sm';
    if (tipo === 'error' || tipo.includes('error')) {
      return `${base} border-red-200 bg-red-50 text-red-800`;
    }
    if (tipo === 'success' || tipo.includes('success')) {
      return `${base} border-emerald-200 bg-emerald-50 text-emerald-800`;
    }
    if (tipo === 'warning' || tipo.includes('warning')) {
      return `${base} border-amber-200 bg-amber-50 text-amber-800`;
    }
    return `${base} border-sky-200 bg-sky-50 text-sky-800`;
  }

  empresaSeleccionada(): string {
    const id = this.tenant.empresaId() ?? this.auth.sesion()?.empresa_actual?.id ?? null;
    return id == null ? '' : String(id);
  }

  cambiarEmpresa(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    if (!value) {
      return;
    }
    this.tenant.setEmpresa(Number(value));
    const actual = this.router.url;
    this.auth.loadMe().subscribe(() => {
      void this.router.navigateByUrl('/', { skipLocationChange: true }).then(() => {
        void this.router.navigateByUrl(actual);
      });
    });
  }

  salir(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/']),
      error: () => this.router.navigate(['/']),
    });
  }

  private cargarEmpresas(): void {
    this.http.get<Pagina<{ id: number; nombre: string; estado: string }>>(`${API}/empresas/`).subscribe({
      next: (pagina) => {
        this.empresas = [...pagina.results].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
      },
    });
  }
}
