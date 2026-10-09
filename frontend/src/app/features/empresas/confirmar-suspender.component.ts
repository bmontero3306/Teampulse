import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Empresa } from './empresa.model';

@Component({
  selector: 'app-empresa-suspender',
  imports: [RouterLink],
  template: `
    <section class="mx-auto max-w-lg">
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Suspender empresa</h1>
      <p class="mt-3 text-slate-600">
        Vas a suspender <strong>{{ empresa().nombre }}</strong>. Los datos y usuarios se conservan, pero nadie de esa
        empresa podrá iniciar sesión hasta que la reactives.
      </p>
      <form class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end" (submit)="$event.preventDefault(); confirmar.emit()">
        <a
          [routerLink]="['/empresas', empresa().id]"
          class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancelar
        </a>
        <button
          type="submit"
          class="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700"
        >
          Confirmar suspensión
        </button>
      </form>
    </section>
  `,
})
export class EmpresaSuspenderComponent {
  empresa = input.required<Empresa>();
  confirmar = output<void>();
}
