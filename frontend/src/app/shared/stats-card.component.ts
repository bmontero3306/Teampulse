import { Component, input } from '@angular/core';

@Component({
  selector: 'app-stats-card',
  template: `
    <article class="rounded-xl border border-slate-200 bg-white p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-slate-500">{{ title() }}</p>
      <p class="mt-2 text-2xl font-semibold text-slate-900">{{ number() }}</p>
    </article>
  `,
})
export class StatsCardComponent {
  title = input('');
  number = input<number | string>(0);
  iconClass = input('');
}
