import { HttpClient } from '@angular/common/http';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { API } from '../../core/api';

interface PaginaAyuda {
  slug: string;
  titulo: string;
  resumen: string;
}

interface GrupoAyuda {
  nombre: string;
  paginas: PaginaAyuda[];
}

/**
 * Equivale a app/templates/app/ayuda/_layout.html.
 * Hay que usarlo como padre de las rutas `ayuda` y `ayuda/:slug`
 * (hoy el markup sigue dentro de resto.pages.ts, que esta sección no edita).
 */
@Component({
  selector: 'app-ayuda-layout',
  imports: [RouterLink, RouterOutlet],
  template: `
    <div class="mx-auto flex max-w-6xl flex-col gap-6 lg:flex-row">
      <aside class="w-full shrink-0 lg:w-64">
        <div class="rounded-xl border border-slate-200 bg-white p-4 lg:sticky lg:top-24">
          <a routerLink="/ayuda" class="text-sm font-semibold text-sky-700 hover:text-sky-900">Ayuda</a>
          <p class="mt-1 text-xs text-slate-500">Guías según tu rol.</p>
          <nav class="mt-4 space-y-4" aria-label="Guías">
            @for (grupo of grupos(); track grupo.nombre) {
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{{ grupo.nombre }}</p>
                <ul class="mt-1 space-y-0.5">
                  @for (item of grupo.paginas; track item.slug) {
                    <li>
                      <a [routerLink]="['/ayuda', item.slug]" [class]="clasesGuia(item.slug)">{{ item.titulo }}</a>
                    </li>
                  }
                </ul>
              </div>
            }
          </nav>
        </div>
      </aside>

      <article class="min-w-0 flex-1">
        <router-outlet />

        @if (paginaActual()) {
          <nav class="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-6 text-sm">
            @if (paginaAnterior(); as anterior) {
              <a [routerLink]="['/ayuda', anterior.slug]" class="font-medium text-sky-700 hover:text-sky-900">
                ← {{ anterior.titulo }}
              </a>
            } @else {
              <a routerLink="/ayuda" class="font-medium text-sky-700 hover:text-sky-900">← Índice</a>
            }
            @if (paginaSiguiente(); as siguiente) {
              <a [routerLink]="['/ayuda', siguiente.slug]" class="font-medium text-sky-700 hover:text-sky-900">
                {{ siguiente.titulo }} →
              </a>
            }
          </nav>
        }
      </article>
    </div>
  `,
})
export class AyudaLayoutComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly title = inject(Title);

  readonly grupos = signal<GrupoAyuda[]>([]);
  readonly paginas = signal<PaginaAyuda[]>([]);
  readonly slug = signal<string | null>(null);

  readonly paginaActual = computed(() => {
    const slug = this.slug();
    if (!slug) {
      return null;
    }
    return this.paginas().find((pagina) => pagina.slug === slug) ?? null;
  });

  readonly paginaAnterior = computed(() => {
    const indice = this.indiceActual();
    if (indice <= 0) {
      return null;
    }
    return this.paginas()[indice - 1];
  });

  readonly paginaSiguiente = computed(() => {
    const indice = this.indiceActual();
    const lista = this.paginas();
    if (indice < 0 || indice >= lista.length - 1) {
      return null;
    }
    return lista[indice + 1];
  });

  constructor() {
    this.slug.set(this.leerSlug());

    effect(() => {
      const titulo = this.paginaActual()?.titulo ?? 'Ayuda';
      this.title.setTitle(`${titulo} · TeamPulse`);
    });

    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe(() => {
      this.slug.set(this.leerSlug());
    });

    this.http.get<{ paginas: PaginaAyuda[]; grupos: GrupoAyuda[] }>(`${API}/ayuda/`).subscribe((data) => {
      this.paginas.set(data.paginas);
      this.grupos.set(data.grupos);
    });
  }

  clasesGuia(slug: string): string {
    const base = 'block rounded-lg px-2 py-1.5 text-sm';
    if (this.slug() === slug) {
      return `${base} bg-sky-50 font-medium text-sky-800`;
    }
    return `${base} text-slate-700 hover:bg-slate-50`;
  }

  private indiceActual(): number {
    const slug = this.slug();
    if (!slug) {
      return -1;
    }
    return this.paginas().findIndex((pagina) => pagina.slug === slug);
  }

  private leerSlug(): string | null {
    let ruta: ActivatedRoute | null = this.route;
    while (ruta?.snapshot) {
      const slug = ruta.snapshot.paramMap.get('slug');
      if (slug) {
        return slug;
      }
      ruta = ruta.firstChild;
    }
    return null;
  }
}
