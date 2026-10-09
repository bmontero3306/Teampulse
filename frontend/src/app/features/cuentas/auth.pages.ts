import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import {
  AYUDA_CLAVE_NUEVA,
  AYUDA_CLAVE_REPETIR,
  CampoCuentaComponent,
  INPUT_CSS,
  MSG_EMAIL,
  MSG_OBLIGATORIO,
  MensajesCuentaComponent,
  PublicoCuentaComponent,
  correoValido,
  enlaceInvalido,
  erroresHttp,
  validarParClaves,
  type MensajeCuenta,
} from './ui-cuenta';

@Component({
  selector: 'app-home',
  imports: [RouterLink],
  template: `
    <main class="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6">
      <p class="text-sm font-medium uppercase tracking-wide text-sky-700">TeamPulse</p>
      <h1 class="mt-2 text-4xl font-semibold tracking-tight text-slate-900">Gestión de desempeño</h1>
      <p class="mt-4 text-slate-600">
        Autoevaluación, evaluación del supervisor, firma de conformidad y reportes ISO 9001.
      </p>
      <a routerLink="/login" class="mt-8 inline-flex w-fit rounded-lg bg-sky-700 px-4 py-2 text-sm font-medium text-white">
        Ingresar
      </a>
    </main>
  `,
})
export class HomePage {}

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink, PublicoCuentaComponent, CampoCuentaComponent, MensajesCuentaComponent],
  template: `
    <app-publico-cuenta>
      <a nav routerLink="/" class="hover:text-slate-700">Inicio</a>
      <section class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center px-6 py-10">
        <h1 class="text-2xl font-semibold text-slate-900">Iniciar sesión</h1>
        <p class="mt-2 text-sm text-slate-600">Ingresá con tu correo electrónico y contraseña.</p>

        <form class="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" (submit)="$event.preventDefault(); enviar()">
          <app-mensajes-cuenta [mensajes]="mensajes()" [general]="general()" />
          <app-campo-cuenta id="id_username" label="Correo electrónico" [required]="true" [error]="error('username')">
            <input
              id="id_username"
              name="username"
              type="email"
              autocomplete="username"
              autofocus
              placeholder="tu@empresa.com"
              [formControl]="email"
              [class]="inputCss"
            />
          </app-campo-cuenta>
          <app-campo-cuenta id="id_password" label="Contraseña" [required]="true" [error]="error('password')">
            <input
              id="id_password"
              name="password"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
              [formControl]="password"
              [class]="inputCss"
            />
          </app-campo-cuenta>
          <button type="submit" class="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700">
            Ingresar
          </button>
          <p class="text-center text-sm">
            <a routerLink="/recuperar" class="font-medium text-sky-700 hover:text-sky-800">Olvidé mi clave</a>
          </p>
        </form>
      </section>
    </app-publico-cuenta>
  `,
})
export class LoginPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly inputCss = INPUT_CSS;
  email = new FormControl('', { nonNullable: true });
  password = new FormControl('', { nonNullable: true });
  errores = signal<Record<string, string>>({});
  general = signal('');
  mensajes = signal<MensajeCuenta[]>([]);

  constructor() {
    inject(Title).setTitle('Iniciar sesión · TeamPulse');
    const aviso = (history.state as { aviso?: string } | null)?.aviso;
    if (aviso) {
      this.mensajes.set([{ tipo: 'success', texto: aviso }]);
      history.replaceState({}, '');
    }
  }

  error(campo: string): string {
    return this.errores()[campo] ?? '';
  }

  enviar(): void {
    const errores: Record<string, string> = {};
    const correo = this.email.value.trim();
    if (!correo) errores['username'] = MSG_OBLIGATORIO;
    else if (!correoValido(correo)) errores['username'] = MSG_EMAIL;
    if (!this.password.value) errores['password'] = MSG_OBLIGATORIO;
    this.errores.set(errores);
    this.general.set('');
    if (Object.keys(errores).length) return;

    this.auth.login(correo, this.password.value).subscribe({
      next: (sesion) => {
        const destino = sesion.debe_cambiar_clave || sesion.usuario.must_change_password
          ? '/clave'
          : sesion.usuario.rol === 'superadmin'
            ? '/empresas'
            : '/dashboard';
        this.router.navigate([destino]);
      },
      error: (err) => {
        const parsed = erroresHttp(err);
        this.general.set(parsed.general);
        this.errores.set(parsed.campos);
      },
    });
  }
}

@Component({
  selector: 'app-recuperar',
  imports: [ReactiveFormsModule, RouterLink, PublicoCuentaComponent, CampoCuentaComponent, MensajesCuentaComponent],
  template: `
    <app-publico-cuenta>
      <a nav routerLink="/login" class="font-medium text-sky-700 hover:text-sky-800">Iniciar sesión</a>
      @if (enviado()) {
        <section class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center px-6 py-10">
          <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 class="text-2xl font-semibold text-slate-900">Revisá tu correo</h1>
            <p class="mt-3 text-sm text-slate-600">
              Si el correo está asociado a una cuenta activa, vas a recibir un enlace para restablecer la contraseña.
              Si no llega, revisá la carpeta de correo no deseado.
            </p>
            <a routerLink="/login" class="mt-6 inline-flex text-sm font-medium text-sky-700 hover:text-sky-800">
              Volver al inicio de sesión
            </a>
          </div>
        </section>
      } @else {
        <section class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center px-6 py-10">
          <h1 class="text-2xl font-semibold text-slate-900">Recuperar contraseña</h1>
          <p class="mt-2 text-sm text-slate-600">
            Ingresá tu correo y te enviaremos un enlace para elegir una nueva clave.
          </p>
          <form class="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" (submit)="$event.preventDefault(); enviar()">
            <app-mensajes-cuenta [general]="general()" />
            <app-campo-cuenta id="id_email" label="Correo electrónico" [required]="true" [error]="errorEmail()">
              <input
                id="id_email"
                name="email"
                type="email"
                autocomplete="email"
                placeholder="tu@empresa.com"
                [formControl]="email"
                [class]="inputCss"
              />
            </app-campo-cuenta>
            <button type="submit" class="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700">
              Enviar enlace
            </button>
            <p class="text-center text-sm">
              <a routerLink="/login" class="font-medium text-sky-700 hover:text-sky-800">Volver al inicio de sesión</a>
            </p>
          </form>
        </section>
      }
    </app-publico-cuenta>
  `,
})
export class RecuperarPage {
  private readonly auth = inject(AuthService);
  private readonly title = inject(Title);
  readonly inputCss = INPUT_CSS;
  email = new FormControl('', { nonNullable: true });
  enviado = signal(false);
  errorEmail = signal('');
  general = signal('');

  constructor() {
    this.title.setTitle('Recuperar contraseña · TeamPulse');
  }

  enviar(): void {
    const correo = this.email.value.trim();
    if (!correo) this.errorEmail.set(MSG_OBLIGATORIO);
    else if (!correoValido(correo)) this.errorEmail.set(MSG_EMAIL);
    else this.errorEmail.set('');
    this.general.set('');
    if (this.errorEmail()) return;

    this.auth.solicitarReset(correo).subscribe({
      next: () => {
        this.enviado.set(true);
        this.title.setTitle('Revisá tu correo · TeamPulse');
      },
      error: (err) => {
        const parsed = erroresHttp(err);
        this.errorEmail.set(parsed.campos['email'] ?? '');
        this.general.set(parsed.general);
      },
    });
  }
}

@Component({
  selector: 'app-reset-confirm',
  imports: [ReactiveFormsModule, RouterLink, PublicoCuentaComponent, CampoCuentaComponent, MensajesCuentaComponent],
  template: `
    <app-publico-cuenta>
      <a nav routerLink="/login" class="font-medium text-sky-700 hover:text-sky-800">Iniciar sesión</a>
      <section class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center px-6 py-10">
        <h1 class="text-2xl font-semibold text-slate-900">Elegí una nueva contraseña</h1>
        @if (enlaceValido()) {
          <form class="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" (submit)="$event.preventDefault(); enviar()">
            <app-mensajes-cuenta [general]="general()" />
            <app-campo-cuenta
              id="id_new_password1"
              label="Contraseña nueva"
              [required]="true"
              [help]="ayudaNueva"
              [error]="error('new_password1')"
            >
              <input
                id="id_new_password1"
                name="new_password1"
                type="password"
                autocomplete="new-password"
                [formControl]="password"
                [class]="inputCss"
              />
            </app-campo-cuenta>
            <app-campo-cuenta
              id="id_new_password2"
              label="Confirmación de contraseña nueva"
              [required]="true"
              [help]="ayudaRepetir"
              [error]="error('new_password2')"
            >
              <input
                id="id_new_password2"
                name="new_password2"
                type="password"
                autocomplete="new-password"
                [formControl]="confirmacion"
                [class]="inputCss"
              />
            </app-campo-cuenta>
            <button type="submit" class="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700">
              Guardar contraseña
            </button>
          </form>
        } @else {
          <div class="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            <p>El enlace no es válido o ya venció. Pedí uno nuevo para recuperar tu clave.</p>
            <a routerLink="/recuperar" class="mt-4 inline-flex font-medium text-sky-700 hover:text-sky-800">
              Recuperar contraseña
            </a>
          </div>
        }
      </section>
    </app-publico-cuenta>
  `,
})
export class ResetConfirmPage {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly inputCss = INPUT_CSS;
  readonly ayudaNueva = AYUDA_CLAVE_NUEVA;
  readonly ayudaRepetir = AYUDA_CLAVE_REPETIR;
  password = new FormControl('', { nonNullable: true });
  confirmacion = new FormControl('', { nonNullable: true });
  errores = signal<Record<string, string>>({});
  general = signal('');
  enlaceValido = signal(true);

  constructor() {
    inject(Title).setTitle('Nueva contraseña · TeamPulse');
    const uid = this.route.snapshot.paramMap.get('uid');
    const token = this.route.snapshot.paramMap.get('token');
    if (!uid || !token) this.enlaceValido.set(false);
  }

  error(campo: string): string {
    return this.errores()[campo] ?? '';
  }

  enviar(): void {
    const errores = validarParClaves(this.password.value, this.confirmacion.value);
    this.errores.set(errores);
    this.general.set('');
    if (Object.keys(errores).length) return;

    const uid = this.route.snapshot.paramMap.get('uid') ?? '';
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    this.auth.confirmarReset(uid, token, this.password.value).subscribe({
      next: (resp) => {
        this.router.navigate(['/login'], { state: { aviso: resp.detail } });
      },
      error: (err) => {
        const parsed = erroresHttp(err);
        if (enlaceInvalido(parsed.general)) {
          this.enlaceValido.set(false);
          return;
        }
        const campos = { ...parsed.campos };
        if (campos['new_password']) {
          campos['new_password2'] = campos['new_password'];
          delete campos['new_password'];
        }
        this.errores.set(campos);
        this.general.set(parsed.general);
      },
    });
  }
}

@Component({
  selector: 'app-clave',
  imports: [ReactiveFormsModule, RouterLink, CampoCuentaComponent, MensajesCuentaComponent],
  template: `
    <section class="mx-auto max-w-lg">
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Cambiar contraseña</h1>
      @if (debeCambiar()) {
        <p class="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Debés cambiar tu contraseña antes de continuar.
        </p>
      }
          <form class="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" (submit)="$event.preventDefault(); enviar()">
        <app-mensajes-cuenta [general]="general()" />
        <app-campo-cuenta id="id_old_password" label="Contraseña antigua" [required]="true" [error]="error('old_password')">
          <input
            id="id_old_password"
            name="old_password"
            type="password"
            autocomplete="current-password"
            autofocus
            [formControl]="actual"
            [class]="inputCss"
          />
        </app-campo-cuenta>
        <app-campo-cuenta
          id="id_new_password1"
          label="Contraseña nueva"
          [required]="true"
          [help]="ayudaNueva"
          [error]="error('new_password1')"
        >
          <input
            id="id_new_password1"
            name="new_password1"
            type="password"
            autocomplete="new-password"
            [formControl]="nueva"
            [class]="inputCss"
          />
        </app-campo-cuenta>
        <app-campo-cuenta
          id="id_new_password2"
          label="Confirmación de contraseña nueva"
          [required]="true"
          [help]="ayudaRepetir"
          [error]="error('new_password2')"
        >
          <input
            id="id_new_password2"
            name="new_password2"
            type="password"
            autocomplete="new-password"
            [formControl]="confirmacion"
            [class]="inputCss"
          />
        </app-campo-cuenta>
        <div class="flex items-center gap-3">
          <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700">
            Guardar
          </button>
          @if (!debeCambiar()) {
            <a routerLink="/perfil" class="text-sm font-medium text-slate-600 hover:text-slate-900">Cancelar</a>
          }
        </div>
      </form>
    </section>
  `,
})
export class ClavePage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly inputCss = INPUT_CSS;
  readonly ayudaNueva = AYUDA_CLAVE_NUEVA;
  readonly ayudaRepetir = AYUDA_CLAVE_REPETIR;
  actual = new FormControl('', { nonNullable: true });
  nueva = new FormControl('', { nonNullable: true });
  confirmacion = new FormControl('', { nonNullable: true });
  errores = signal<Record<string, string>>({});
  general = signal('');

  constructor() {
    inject(Title).setTitle('Cambiar contraseña · TeamPulse');
  }

  debeCambiar(): boolean {
    const sesion = this.auth.sesion();
    if (!sesion) return true;
    return sesion.debe_cambiar_clave || sesion.usuario.must_change_password;
  }

  error(campo: string): string {
    return this.errores()[campo] ?? '';
  }

  enviar(): void {
    const errores = validarParClaves(this.nueva.value, this.confirmacion.value);
    if (!this.actual.value) errores['old_password'] = MSG_OBLIGATORIO;
    this.errores.set(errores);
    this.general.set('');
    if (Object.keys(errores).length) return;

    this.auth.cambiarClave(this.actual.value, this.nueva.value).subscribe({
      next: (sesion) => {
        const destino = sesion.usuario.rol === 'superadmin' ? '/empresas' : '/dashboard';
        this.router.navigate([destino]);
      },
      error: (err) => {
        const parsed = erroresHttp(err);
        const campos = { ...parsed.campos };
        if (campos['new_password']) {
          campos['new_password2'] = campos['new_password'];
          delete campos['new_password'];
        }
        this.errores.set(campos);
        this.general.set(parsed.general);
      },
    });
  }
}

@Component({
  selector: 'app-perfil',
  imports: [RouterLink],
  template: `
    <section class="mx-auto max-w-2xl">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Mi perfil</h1>
          <p class="mt-1 text-sm text-slate-600">Datos de solo lectura. Para cambiar la clave usá el botón.</p>
        </div>
        <a routerLink="/clave" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700">
          Cambiar clave
        </a>
      </div>

      @if (auth.sesion(); as sesion) {
        <dl class="mt-6 divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Nombre</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ nombre(sesion.usuario.first_name, sesion.usuario.last_name) }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Correo</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ sesion.usuario.email }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">DNI</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ texto(sesion.usuario.dni) }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Rol</dt>
            <dd class="text-sm capitalize text-slate-900 sm:col-span-2">{{ sesion.usuario.rol_display }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Empresa</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ texto(sesion.usuario.empresa_nombre) }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Área</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ texto(sesion.usuario.area_nombre) }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Puesto</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ texto(sesion.usuario.puesto_nombre) }}</dd>
          </div>
          <div class="grid gap-1 px-6 py-4 sm:grid-cols-3 sm:gap-4">
            <dt class="text-sm font-medium text-slate-500">Supervisor</dt>
            <dd class="text-sm text-slate-900 sm:col-span-2">{{ texto(sesion.usuario.supervisor_nombre) }}</dd>
          </div>
        </dl>
      }
    </section>
  `,
})
export class PerfilPage {
  readonly auth = inject(AuthService);

  constructor() {
    inject(Title).setTitle('Mi perfil · TeamPulse');
  }

  nombre(first: string, last: string): string {
    return this.texto(`${first} ${last}`);
  }

  texto(valor: string | null | undefined): string {
    const limpio = (valor ?? '').trim();
    return limpio || '—';
  }
}
