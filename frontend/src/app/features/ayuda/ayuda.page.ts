import { AfterViewChecked, Component, computed, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { gruposAyuda } from './ayuda.catalogo';

declare const lucide: { createIcons: () => void } | undefined;

/** Índice de ayuda. Copia app/templates/app/ayuda/index.html. */
@Component({
  selector: 'app-ayuda-indice',
  imports: [RouterLink],
  template: `
    <section class="mx-auto max-w-5xl">
      <header class="mb-8">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Ayuda</h1>
        <p class="mt-1 max-w-2xl text-sm text-slate-600">
          Cómo está armado TeamPulse: las piezas del sistema, el proceso de evaluación, los estados y qué hace cada
          rol. Las guías que ves dependen de tu permiso.
        </p>
      </header>

      <div class="space-y-8">
        @for (grupo of grupos(); track grupo.nombre) {
          <section>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">{{ grupo.nombre }}</h2>
            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              @for (item of grupo.paginas; track item.slug) {
                <a
                  [routerLink]="['/ayuda', item.slug]"
                  class="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 hover:border-sky-200 hover:bg-sky-50/40"
                >
                  <span
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-50 text-sky-700"
                    aria-hidden="true"
                  >
                    <i [attr.data-lucide]="item.icono" class="h-5 w-5"></i>
                  </span>
                  <span>
                    <span class="block font-medium text-slate-900">{{ item.titulo }}</span>
                    <span class="mt-0.5 block text-sm text-slate-600">{{ item.resumen }}</span>
                  </span>
                </a>
              }
            </div>
          </section>
        }
      </div>
    </section>
  `,
})
export class AyudaPage implements AfterViewChecked {
  private readonly auth = inject(AuthService);
  private readonly title = inject(Title);
  readonly grupos = computed(() => gruposAyuda(this.auth.sesion()?.usuario.rol));

  constructor() {
    this.title.setTitle('Ayuda · TeamPulse');
  }

  ngAfterViewChecked(): void {
    lucide?.createIcons();
  }
}
