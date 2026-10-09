import { AfterViewChecked, Component, inject } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';

declare const lucide: { createIcons: (opts?: { attrs?: Record<string, string> }) => void } | undefined;

/** Equivale a theme/templates/base.html (header público + main). */
@Component({
  selector: 'app-public-layout',
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <a routerLink="/" class="text-lg font-semibold tracking-tight text-sky-700">
          TeamPulse
        </a>
        <nav class="text-sm text-slate-500">
          @if (enlaceNav(); as enlace) {
            <a [routerLink]="enlace.href" [class]="enlace.clase">{{ enlace.texto }}</a>
          }
        </nav>
      </div>
    </header>

    <main>
      <router-outlet />
    </main>
  `,
})
export class PublicLayoutComponent implements AfterViewChecked {
  private readonly router = inject(Router);

  ngAfterViewChecked(): void {
    lucide?.createIcons({ attrs: { 'stroke-width': '1.8' } });
  }

  /**
   * Textos del `{% block nav %}` de home, login y recuperar clave.
   * En Django los llena cada template hijo; acá se resuelven por ruta
   * para no editar las páginas de cuentas.
   */
  enlaceNav(): { href: string; texto: string; clase: string } | null {
    const path = this.router.url.split('?')[0].split('#')[0];
    if (path === '/login') {
      return { href: '/', texto: 'Inicio', clase: 'hover:text-slate-700' };
    }
    if (path === '/' || path.startsWith('/recuperar')) {
      return {
        href: '/login',
        texto: 'Iniciar sesión',
        clase: 'font-medium text-sky-700 hover:text-sky-800',
      };
    }
    return null;
  }
}
