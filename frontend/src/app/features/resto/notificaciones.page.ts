// Alineada a notificaciones/templates/notificaciones/lista.html.
// La ruta /notificaciones sigue cargando NotificacionesPage desde resto.pages.ts.
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { Pagina } from '../../core/models';
import { AlertService } from '../../shared/alert.service';

interface Notificacion {
  id: number;
  titulo: string;
  mensaje: string;
  leida: boolean;
  created_at: string;
  url: string;
}

const PAGE_SIZE = 20;
const ZONA = 'America/Argentina/Buenos_Aires';

function fechaNotificacion(iso: string): string {
  const fmt = new Intl.DateTimeFormat('es-AR', {
    timeZone: ZONA,
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
  const partes: Record<string, string> = {};
  for (const parte of fmt.formatToParts(new Date(iso))) {
    if (parte.type !== 'literal') {
      partes[parte.type] = parte.value;
    }
  }
  return `${partes['day']} de ${partes['month']} de ${partes['year']} a las ${partes['hour']}:${partes['minute']}`;
}

@Component({
  selector: 'app-notificaciones',
  template: `
    <section>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Notificaciones</h1>
          <p class="mt-1 text-sm text-slate-600">
            Avisos in-app de tu cuenta. Los correos también se envían a {{ auth.sesion()?.usuario?.email }}.
          </p>
        </div>
        @if (lista().length) {
          <form (submit)="todas($event)">
            <button
              type="submit"
              class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Marcar todas como leídas
            </button>
          </form>
        }
      </div>

      @if (count() > 0) {
        <ul class="mt-6 space-y-3">
          @for (item of lista(); track item.id) {
            <li [class]="item.leida
              ? 'rounded-xl border border-slate-200 bg-white px-4 py-3'
              : 'rounded-xl border border-sky-200 bg-sky-50 px-4 py-3'">
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="font-medium text-slate-900">{{ item.titulo }}</p>
                  <p class="mt-1 text-sm text-slate-600">{{ item.mensaje }}</p>
                  <p class="mt-2 text-xs text-slate-400">{{ fecha(item.created_at) }}</p>
                </div>
                <div class="flex items-center gap-2">
                  @if (!item.leida) {
                    <span class="rounded-full bg-sky-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">Nueva</span>
                  }
                  <a
                    href=""
                    class="rounded-lg px-2 py-1 text-sm font-medium text-sky-700 hover:bg-sky-100"
                    (click)="leer(item, $event)"
                  >
                    {{ etiqueta(item) }}
                  </a>
                </div>
              </div>
            </li>
          }
        </ul>
        @if (paginas() > 1) {
          <nav class="mt-6 flex items-center justify-between text-sm text-slate-600">
            @if (page() > 1) {
              <a href="" class="rounded-lg px-3 py-1.5 hover:bg-slate-100" (click)="ir(page() - 1, $event)">Anterior</a>
            } @else {
              <span></span>
            }
            <span>Página {{ page() }} de {{ paginas() }}</span>
            @if (page() < paginas()) {
              <a href="" class="rounded-lg px-3 py-1.5 hover:bg-slate-100" (click)="ir(page() + 1, $event)">Siguiente</a>
            } @else {
              <span></span>
            }
          </nav>
        }
      } @else if (cargada()) {
        <p class="mt-8 rounded-xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
          No tenés notificaciones.
        </p>
      }
    </section>
  `,
})
export class NotificacionesPage {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly alertas = inject(AlertService);
  readonly auth = inject(AuthService);
  lista = signal<Notificacion[]>([]);
  count = signal(0);
  page = signal(1);
  cargada = signal(false);

  constructor() {
    inject(Title).setTitle('Notificaciones · TeamPulse');
    this.cargar();
  }

  paginas(): number {
    return Math.max(1, Math.ceil(this.count() / PAGE_SIZE));
  }

  fecha(iso: string): string {
    return fechaNotificacion(iso);
  }

  etiqueta(item: Notificacion): string {
    if (item.url) {
      return 'Ver';
    }
    if (item.leida) {
      return 'Abrir';
    }
    return 'Marcar leída';
  }

  cargar(): void {
    this.http
      .get<Pagina<Notificacion>>(`${API}/notificaciones/`, { params: { page: String(this.page()) } })
      .subscribe((p) => {
        this.lista.set(p.results);
        this.count.set(p.count);
        this.cargada.set(true);
      });
  }

  ir(pagina: number, event: Event): void {
    event.preventDefault();
    this.page.set(pagina);
    this.cargar();
  }

  leer(item: Notificacion, event: Event): void {
    event.preventDefault();
    this.http.post<Notificacion>(`${API}/notificaciones/${item.id}/leer/`, {}).subscribe((actualizada) => {
      this.auth.loadMe().subscribe();
      const url = actualizada.url || '';
      if (url.startsWith('/')) {
        this.router.navigateByUrl(url);
        return;
      }
      this.cargar();
    });
  }

  todas(event: Event): void {
    event.preventDefault();
    this.http.post<{ detail: string }>(`${API}/notificaciones/leer-todas/`, {}).subscribe((res) => {
      this.alertas.success(res.detail || 'Todas las notificaciones se marcaron como leídas.');
      this.page.set(1);
      this.auth.loadMe().subscribe();
      this.cargar();
    });
  }
}
