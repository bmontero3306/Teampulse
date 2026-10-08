import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { API } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { AlertService } from '../../shared/alert.service';
import { BadgeComponent } from '../../shared/badge.component';
import { ButtonComponent } from '../../shared/button.component';
import { mensajeError } from '../../shared/errores';

interface Respuesta {
  id: number;
  competencia: string;
  categoria: string;
  tipo_item: string;
  escala_min: number;
  escala_max: number;
  comentario_empleado_obligatorio: boolean;
  comentario_supervisor_obligatorio: boolean;
  puntaje_empleado: number | null;
  comentario_empleado: string;
  puntaje_supervisor: number | null;
  comentario_supervisor: string;
  brecha: number | null;
}

interface Evaluacion {
  id: number;
  estado: string;
  estado_display: string;
  ciclo_nombre: string;
  evaluado?: { id: number; nombre: string };
  evaluador?: { id: number; nombre: string } | null;
  puesto_nombre: string;
  sin_evaluador: boolean;
  feedback_supervisor?: string;
  reunion_fecha?: string | null;
  reunion_notas?: string;
  firma_hash?: string;
  comparacion_revelada?: boolean;
  puede_firmar?: boolean;
  puede_reunion?: boolean;
  respuestas?: Respuesta[];
}

@Component({
  selector: 'app-mias',
  imports: [RouterLink, BadgeComponent],
  template: `
    <h1 class="text-2xl font-semibold">Mis evaluaciones</h1>
    <ul class="mt-4 divide-y rounded-xl border border-slate-200 bg-white">
      @for (ev of lista(); track ev.id) {
        <li class="flex items-center justify-between px-4 py-3 text-sm">
          <a [routerLink]="destino(ev)" class="font-medium text-sky-800">{{ ev.ciclo_nombre }}</a>
          <app-badge [label]="ev.estado_display" />
        </li>
      } @empty { <li class="px-4 py-6 text-sm text-slate-500">No tenés evaluaciones.</li> }
    </ul>
  `,
})
export class MiasPage {
  private readonly http = inject(HttpClient);
  lista = signal<Evaluacion[]>([]);
  constructor() {
    this.http.get<Evaluacion[]>(`${API}/evaluaciones/mias/`).subscribe((lista) => this.lista.set(lista));
  }
  destino(ev: Evaluacion): string[] {
    if (ev.estado === 'pendiente_auto' || ev.estado === 'auto_borrador') {
      return ['/evaluaciones', String(ev.id), 'autoevaluacion'];
    }
    return ['/evaluaciones', String(ev.id), 'resultado'];
  }
}

@Component({
  selector: 'app-equipo',
  imports: [RouterLink, BadgeComponent],
  template: `
    <h1 class="text-2xl font-semibold">Equipo</h1>
    <ul class="mt-4 divide-y rounded-xl border border-slate-200 bg-white">
      @for (ev of lista(); track ev.id) {
        <li class="flex items-center justify-between px-4 py-3 text-sm">
          <a [routerLink]="['/evaluaciones', ev.id, 'supervisar']" class="font-medium text-sky-800">
            {{ ev.evaluado?.nombre }} · {{ ev.ciclo_nombre }}
          </a>
          <app-badge [label]="ev.estado_display" />
        </li>
      }
    </ul>
  `,
})
export class EquipoPage {
  private readonly http = inject(HttpClient);
  lista = signal<Evaluacion[]>([]);
  constructor() {
    this.http.get<Evaluacion[]>(`${API}/evaluaciones/equipo/`).subscribe((lista) => this.lista.set(lista));
  }
}

@Component({
  selector: 'app-flujo',
  imports: [RouterLink, ButtonComponent, BadgeComponent],
  template: `
    @if (ev(); as actual) {
      <p class="text-sm text-slate-500">{{ actual.ciclo_nombre }} · {{ actual.puesto_nombre }}</p>
      <h1 class="text-2xl font-semibold">{{ titulo() }}</h1>
      <p class="mt-1"><app-badge [label]="actual.estado_display" /></p>
      <div class="mt-6 space-y-4">
        @for (item of actual.respuestas ?? []; track item.id) {
          <article class="rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <p class="font-medium">{{ item.competencia }}</p>
            @if (modo() !== 'resultado' && item.tipo_item === 'escala') {
              <label class="mt-2 block">Puntaje ({{ item.escala_min }} a {{ item.escala_max }})
                <input type="number" class="mt-1 w-32 rounded-lg border border-slate-300 px-2 py-1" [value]="puntaje(item)" (input)="setPuntaje(item, $event)" />
              </label>
            } @else if (item.tipo_item === 'escala') {
              <p class="mt-2 text-slate-600">Empleado: {{ item.puntaje_empleado ?? '—' }} · Supervisor: {{ item.puntaje_supervisor ?? '—' }} · Brecha: {{ item.brecha ?? '—' }}</p>
            }
            @if (modo() !== 'resultado') {
              <label class="mt-2 block">Comentario
                <textarea class="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1" rows="2" [value]="comentario(item)" (input)="setComentario(item, $event)"></textarea>
              </label>
            } @else {
              <p class="mt-2 text-slate-600">{{ item.comentario_empleado }}</p>
              @if (item.comentario_supervisor) { <p class="text-slate-600">Supervisor: {{ item.comentario_supervisor }}</p> }
            }
          </article>
        }
      </div>
      @if (modo() === 'supervisar') {
        <label class="mt-4 block text-sm">Feedback del supervisor
          <textarea class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" rows="3" [value]="feedback()" (input)="feedback.set(valor($event))"></textarea>
        </label>
        <label class="mt-2 flex items-center gap-2 text-sm">
          <input type="checkbox" [checked]="reunion()" (change)="reunion.set($any($event.target).checked)" />
          Habilitar reunión de feedback
        </label>
        <div class="mt-4 flex gap-2">
          <app-button color="secondary" label="Guardar borrador" (buttonClick)="guardarSupervisor(false)" />
          <app-button label="Cerrar evaluación" (buttonClick)="guardarSupervisor(true)" />
        </div>
      }
      @if (modo() === 'auto') {
        <div class="mt-4 flex gap-2">
          <app-button color="secondary" label="Guardar borrador" (buttonClick)="guardarAuto(false)" />
          <app-button label="Enviar" (buttonClick)="guardarAuto(true)" />
        </div>
      }
      @if (modo() === 'resultado') {
        @if (actual.feedback_supervisor) {
          <p class="mt-4 rounded-xl bg-slate-50 p-4 text-sm">{{ actual.feedback_supervisor }}</p>
        }
        @if (actual.puede_reunion) {
          <div class="mt-4 space-y-2">
            <input type="datetime-local" class="rounded-lg border border-slate-300 px-3 py-2 text-sm" #fecha />
            <textarea class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows="3" placeholder="Notas de la reunión" #notas></textarea>
            <div class="flex gap-2">
              <app-button label="Registrar reunión" (buttonClick)="registrar(fecha.value, notas.value)" />
              <app-button color="secondary" label="Omitir reunión" (buttonClick)="omitir()" />
            </div>
          </div>
        }
        @if (actual.puede_firmar) {
          <div class="mt-4 space-y-2">
            <textarea class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows="2" placeholder="Observación (opcional)" #obs></textarea>
            <app-button label="Firmar conformidad" (buttonClick)="firmar(obs.value)" />
          </div>
        }
        @if (actual.firma_hash) {
          <p class="mt-4 text-xs text-slate-500">Firma {{ actual.firma_hash }}</p>
        }
        <button type="button" class="mt-4 text-sm text-sky-700" (click)="descargar()">Descargar PDF</button>
        @if (puedeReasignar()) {
          <div class="mt-6 max-w-md space-y-2">
            <label class="block text-sm">Reasignar evaluador
              <select class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" #evaluador>
                @for (candidato of candidatos(); track candidato.id) {
                  <option [value]="candidato.id">{{ candidato.nombre }} · {{ candidato.rol }}</option>
                }
              </select>
            </label>
            <app-button size="sm" label="Reasignar" (buttonClick)="reasignar(evaluador.value)" />
          </div>
        }
      }
      <a routerLink="/evaluaciones/mias" class="mt-6 block text-sm text-slate-500">Volver</a>
    }
  `,
})
export class FlujoPage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  ev = signal<Evaluacion | null>(null);
  modo = signal<'auto' | 'supervisar' | 'resultado'>('auto');
  feedback = signal('');
  reunion = signal(false);
  candidatos = signal<{ id: number; nombre: string; rol: string }[]>([]);

  constructor() {
    const modo = this.route.snapshot.data['modo'] as 'auto' | 'supervisar' | 'resultado';
    this.modo.set(modo);
    const id = this.route.snapshot.paramMap.get('id');
    const path = modo === 'auto' ? 'autoevaluacion' : modo === 'supervisar' ? 'supervisar' : 'resultado';
    this.http.get<Evaluacion>(`${API}/evaluaciones/${id}/${path}/`).subscribe((ev) => {
      this.ev.set(ev);
      this.feedback.set(ev.feedback_supervisor ?? '');
    });
    if (modo === 'resultado' && this.puedeReasignar()) {
      this.http
        .get<{ id: number; nombre: string; rol: string }[]>(`${API}/evaluaciones/${id}/reasignar/`)
        .subscribe((lista) => this.candidatos.set(lista));
    }
  }

  puedeReasignar(): boolean {
    const rol = this.auth.sesion()?.usuario.rol;
    return rol === 'admin_rrhh' || rol === 'superadmin';
  }

  titulo(): string {
    return this.modo() === 'auto' ? 'Autoevaluación' : this.modo() === 'supervisar' ? 'Evaluar' : 'Resultado';
  }

  puntaje(item: Respuesta): number | null {
    return this.modo() === 'supervisar' ? item.puntaje_supervisor : item.puntaje_empleado;
  }

  comentario(item: Respuesta): string {
    return this.modo() === 'supervisar' ? item.comentario_supervisor : item.comentario_empleado;
  }

  setPuntaje(item: Respuesta, event: Event): void {
    const valor = (event.target as HTMLInputElement).value;
    const numero = valor === '' ? null : Number(valor);
    if (this.modo() === 'supervisar') item.puntaje_supervisor = numero;
    else item.puntaje_empleado = numero;
  }

  setComentario(item: Respuesta, event: Event): void {
    const valor = (event.target as HTMLTextAreaElement).value;
    if (this.modo() === 'supervisar') item.comentario_supervisor = valor;
    else item.comentario_empleado = valor;
  }

  valor(event: Event): string {
    return (event.target as HTMLTextAreaElement).value;
  }

  guardarAuto(enviar: boolean): void {
    const actual = this.ev();
    if (!actual) return;
    this.http
      .put<Evaluacion>(`${API}/evaluaciones/${actual.id}/autoevaluacion/`, {
        enviar,
        respuestas: (actual.respuestas ?? []).map((item) => ({
          id: item.id,
          puntaje_empleado: item.puntaje_empleado,
          comentario_empleado: item.comentario_empleado,
        })),
      })
      .subscribe({
        next: (ev) => {
          this.ev.set(ev);
          this.alertas.success(enviar ? 'Autoevaluación enviada.' : 'Borrador guardado.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  guardarSupervisor(cerrar: boolean): void {
    const actual = this.ev();
    if (!actual) return;
    this.http
      .put<Evaluacion>(`${API}/evaluaciones/${actual.id}/supervisar/`, {
        cerrar,
        habilitar_reunion: this.reunion(),
        feedback_supervisor: this.feedback(),
        respuestas: (actual.respuestas ?? []).map((item) => ({
          id: item.id,
          puntaje_supervisor: item.puntaje_supervisor,
          comentario_supervisor: item.comentario_supervisor,
        })),
      })
      .subscribe({
        next: (ev) => {
          this.ev.set(ev);
          this.alertas.success(cerrar ? 'Evaluación cerrada.' : 'Borrador guardado.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  registrar(fecha: string, notas: string): void {
    const actual = this.ev();
    if (!actual) return;
    this.http
      .post<Evaluacion>(`${API}/evaluaciones/${actual.id}/reunion/`, {
        reunion_fecha: new Date(fecha).toISOString(),
        reunion_notas: notas,
      })
      .subscribe({
        next: (ev) => this.ev.set({ ...ev, puede_reunion: false, puede_firmar: ev.estado === 'pendiente_conformidad' }),
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  omitir(): void {
    const actual = this.ev();
    if (!actual) return;
    this.http.post<Evaluacion>(`${API}/evaluaciones/${actual.id}/omitir-reunion/`, {}).subscribe({
      next: (ev) => this.ev.set(ev),
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  firmar(observacion: string): void {
    const actual = this.ev();
    if (!actual) return;
    this.http.post<Evaluacion>(`${API}/evaluaciones/${actual.id}/firmar/`, { observacion }).subscribe({
      next: (ev) => {
        this.ev.set(ev);
        this.alertas.success('Conformidad registrada.');
      },
      error: (err) => this.alertas.error(mensajeError(err)),
    });
  }

  reasignar(evaluadorId: string): void {
    const actual = this.ev();
    if (!actual || !evaluadorId) return;
    this.http
      .post<Evaluacion>(`${API}/evaluaciones/${actual.id}/reasignar/`, { evaluador: Number(evaluadorId) })
      .subscribe({
        next: (ev) => {
          this.ev.set(ev);
          this.alertas.success('Evaluador reasignado.');
        },
        error: (err) => this.alertas.error(mensajeError(err)),
      });
  }

  descargar(): void {
    const id = this.ev()?.id;
    if (!id) return;
    this.http.get(`${API}/evaluaciones/${id}/resultado.pdf`, { responseType: 'blob' }).subscribe((blob) => {
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `evaluacion-${id}.pdf`;
      enlace.click();
      URL.revokeObjectURL(url);
    });
  }
}
