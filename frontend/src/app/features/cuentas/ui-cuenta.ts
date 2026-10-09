import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

export const INPUT_CSS =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';

export const SELECT_FILTRO_CSS =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';

export const MSG_OBLIGATORIO = 'Este campo es obligatorio.';
export const MSG_EMAIL = 'Introduzca una dirección de email válida.';
export const MSG_CLAVE_CORTA = 'Su contraseña debe contener por lo menos 8 caracteres.';
export const MSG_CLAVE_NUMERICA = 'Su contraseña no puede estar formada exclusivamente por números.';
export const MSG_CLAVE_DISTINTA = 'Los dos campos de contraseñas no coinciden entre si.';

export const AYUDA_CLAVE_NUEVA =
  '<ul><li>Su contraseña no puede ser similar a otros componentes de su información personal.</li>' +
  '<li>Su contraseña debe contener por lo menos 8 caracteres.</li>' +
  '<li>Su contraseña no puede ser una contraseña usada muy comúnmente.</li>' +
  '<li>Su contraseña no puede estar formada exclusivamente por números.</li></ul>';

export const AYUDA_CLAVE_REPETIR =
  'Introduzca la misma contraseña nuevamente, para poder verificar la misma.';

export const AYUDA_SUPERVISOR =
  'Si el puesto tiene superior, el supervisor se completa automáticamente.';

export interface MensajeCuenta {
  tipo: 'success' | 'error' | 'info';
  texto: string;
}

export interface ErroresHttp {
  general: string;
  campos: Record<string, string>;
}

export function correoValido(valor: string): boolean {
  const email = valor.trim();
  if (!email || email.length > 254 || /\s/.test(email)) return false;
  const partes = email.split('@');
  if (partes.length !== 2) return false;
  const [local, dominio] = partes;
  return Boolean(local && dominio && dominio.includes('.') && !dominio.startsWith('.') && !dominio.endsWith('.'));
}

export function validarParClaves(clave: string, confirmacion: string): Record<string, string> {
  const errores: Record<string, string> = {};
  if (!clave) errores['new_password1'] = MSG_OBLIGATORIO;
  if (!confirmacion) errores['new_password2'] = MSG_OBLIGATORIO;
  if (!confirmacion) return errores;
  if (clave && clave !== confirmacion) {
    errores['new_password2'] = MSG_CLAVE_DISTINTA;
    return errores;
  }
  if (confirmacion.length < 8) errores['new_password2'] = MSG_CLAVE_CORTA;
  else if (/^\d+$/.test(confirmacion)) errores['new_password2'] = MSG_CLAVE_NUMERICA;
  return errores;
}

function textoPlano(valor: unknown): string {
  if (typeof valor === 'string') return valor;
  if (Array.isArray(valor)) return valor.map(textoPlano).filter(Boolean).join(' ');
  if (valor && typeof valor === 'object' && 'detail' in valor) {
    return textoPlano((valor as { detail: unknown }).detail);
  }
  return '';
}

export function erroresHttp(error: unknown): ErroresHttp {
  const cuerpo = (error as { error?: unknown })?.error;
  const campos: Record<string, string> = {};
  const generales: string[] = [];
  if (cuerpo == null || cuerpo === '') {
    return { general: 'No se pudo completar la operación.', campos };
  }
  if (typeof cuerpo === 'string' || Array.isArray(cuerpo)) {
    return { general: textoPlano(cuerpo) || 'No se pudo completar la operación.', campos };
  }
  if (typeof cuerpo === 'object') {
    for (const [clave, valor] of Object.entries(cuerpo as Record<string, unknown>)) {
      const texto = textoPlano(valor);
      if (!texto) continue;
      if (clave === 'detail' || clave === 'non_field_errors') generales.push(texto);
      else campos[clave] = texto;
    }
  }
  return { general: generales.join(' '), campos };
}

export function enlaceInvalido(detail: string): boolean {
  return detail.includes('El enlace no es válido');
}

@Component({
  selector: 'app-publico-cuenta',
  imports: [RouterLink],
  template: `
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <a routerLink="/" class="text-lg font-semibold tracking-tight text-sky-700">TeamPulse</a>
        <nav class="text-sm text-slate-500">
          <ng-content select="[nav]" />
        </nav>
      </div>
    </header>
    <main>
      <ng-content />
    </main>
  `,
})
export class PublicoCuentaComponent {}

@Component({
  selector: 'app-campo-cuenta',
  template: `
    <div class="space-y-1">
      <label [attr.for]="id()" class="block text-sm font-medium text-slate-700">
        {{ label() }}
        @if (required()) {
          <span class="text-red-600">*</span>
        }
      </label>
      <ng-content />
      @if (help()) {
        <p class="text-xs text-slate-500" [innerHTML]="help()"></p>
      }
      @if (error()) {
        <p class="text-sm text-red-600">{{ error() }}</p>
      }
    </div>
  `,
})
export class CampoCuentaComponent {
  id = input.required<string>();
  label = input.required<string>();
  required = input(false);
  help = input('');
  error = input('');
}

@Component({
  selector: 'app-mensajes-cuenta',
  template: `
    @if (mensajes().length) {
      <ul class="mb-4 space-y-2">
        @for (mensaje of mensajes(); track $index) {
          <li [class]="'rounded-lg border px-4 py-3 text-sm ' + clase(mensaje.tipo)">{{ mensaje.texto }}</li>
        }
      </ul>
    }
    @if (general()) {
      <div class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
        {{ general() }}
      </div>
    }
  `,
})
export class MensajesCuentaComponent {
  mensajes = input<MensajeCuenta[]>([]);
  general = input('');

  clase(tipo: MensajeCuenta['tipo']): string {
    if (tipo === 'error') return 'border-red-200 bg-red-50 text-red-800';
    if (tipo === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
    return 'border-sky-200 bg-sky-50 text-sky-800';
  }
}
