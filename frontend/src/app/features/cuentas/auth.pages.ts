import { Component, inject, signal } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { AlertComponent } from '../../shared/alert.component';
import { ButtonComponent } from '../../shared/button.component';
import { mensajeError } from '../../shared/errores';
import { InputTextComponent } from '../../shared/input-text.component';

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
  imports: [FormsModule, ReactiveFormsModule, RouterLink, InputTextComponent, ButtonComponent, AlertComponent],
  template: `
    <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 class="text-2xl font-semibold text-slate-900">Ingresar</h1>
      <form class="mt-6 space-y-4" (ngSubmit)="enviar()">
        <app-input-text label="Correo electrónico" type="email" autocomplete="username" [required]="true" [control]="email" />
        <app-input-text label="Contraseña" type="password" autocomplete="current-password" [required]="true" [control]="password" />
        @if (error()) { <p class="text-sm text-rose-600">{{ error() }}</p> }
        <app-button type="submit" label="Entrar" [disabled]="cargando()" />
      </form>
      <a routerLink="/recuperar" class="mt-4 text-sm text-sky-700">Olvidé mi clave</a>
    </main>
    <app-alert />
  `,
})
export class LoginPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  email = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] });
  password = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  error = signal('');
  cargando = signal(false);

  enviar(): void {
    if (this.email.invalid || this.password.invalid) {
      this.email.markAllAsTouched();
      this.password.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.auth.login(this.email.value, this.password.value).subscribe({
      next: (sesion) => {
        const destino = sesion.debe_cambiar_clave || sesion.usuario.must_change_password
          ? '/clave'
          : sesion.usuario.rol === 'superadmin'
            ? '/empresas'
            : '/dashboard';
        this.router.navigate([destino]);
      },
      error: (err) => {
        this.error.set(mensajeError(err));
        this.cargando.set(false);
      },
    });
  }
}

@Component({
  selector: 'app-recuperar',
  imports: [FormsModule, ReactiveFormsModule, RouterLink, InputTextComponent, ButtonComponent],
  template: `
    <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 class="text-2xl font-semibold">Recuperar contraseña</h1>
      @if (enviado()) {
        <p class="mt-4 text-sm text-slate-600">{{ mensaje() }}</p>
      } @else {
        <form class="mt-6 space-y-4" (ngSubmit)="enviar()">
          <app-input-text label="Correo electrónico" type="email" [required]="true" [control]="email" />
          <app-button type="submit" label="Enviar enlace" />
        </form>
      }
      <a routerLink="/login" class="mt-4 text-sm text-sky-700">Volver al ingreso</a>
    </main>
  `,
})
export class RecuperarPage {
  private readonly auth = inject(AuthService);
  email = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] });
  enviado = signal(false);
  mensaje = signal('');

  enviar(): void {
    this.auth.solicitarReset(this.email.value).subscribe((resp) => {
      this.mensaje.set(resp.detail);
      this.enviado.set(true);
    });
  }
}

@Component({
  selector: 'app-reset-confirm',
  imports: [FormsModule, ReactiveFormsModule, RouterLink, InputTextComponent, ButtonComponent],
  template: `
    <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 class="text-2xl font-semibold">Nueva contraseña</h1>
      @if (listo()) {
        <p class="mt-4 text-sm text-slate-600">{{ mensaje() }}</p>
        <a routerLink="/login" class="mt-4 text-sm text-sky-700">Ingresar</a>
      } @else {
        <form class="mt-6 space-y-4" (ngSubmit)="enviar()">
          <app-input-text label="Nueva contraseña" type="password" [required]="true" [control]="password" />
          @if (error()) { <p class="text-sm text-rose-600">{{ error() }}</p> }
          <app-button type="submit" label="Guardar" />
        </form>
      }
    </main>
  `,
})
export class ResetConfirmPage {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  password = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.minLength(8)] });
  error = signal('');
  listo = signal(false);
  mensaje = signal('');

  enviar(): void {
    const uid = this.route.snapshot.paramMap.get('uid') ?? '';
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    this.auth.confirmarReset(uid, token, this.password.value).subscribe({
      next: (resp) => {
        this.mensaje.set(resp.detail);
        this.listo.set(true);
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }
}

@Component({
  selector: 'app-clave',
  imports: [FormsModule, ReactiveFormsModule, InputTextComponent, ButtonComponent],
  template: `
    <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 class="text-2xl font-semibold">Cambiar contraseña</h1>
      <p class="mt-2 text-sm text-slate-600">Tenés que definir una clave nueva antes de seguir.</p>
      <form class="mt-6 space-y-4" (ngSubmit)="enviar()">
        <app-input-text label="Contraseña actual" type="password" [control]="actual" />
        <app-input-text label="Nueva contraseña" type="password" [control]="nueva" />
        @if (error()) { <p class="text-sm text-rose-600">{{ error() }}</p> }
        <app-button type="submit" label="Actualizar" />
      </form>
    </main>
  `,
})
export class ClavePage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  actual = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  nueva = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.minLength(8)] });
  error = signal('');

  enviar(): void {
    this.auth.cambiarClave(this.actual.value, this.nueva.value).subscribe({
      next: (sesion) => {
        const destino = sesion.usuario.rol === 'superadmin' ? '/empresas' : '/dashboard';
        this.router.navigate([destino]);
      },
      error: (err) => this.error.set(mensajeError(err)),
    });
  }
}

@Component({
  selector: 'app-perfil',
  template: `
    <h1 class="text-2xl font-semibold">Perfil</h1>
    @if (auth.sesion(); as sesion) {
      <dl class="mt-6 grid max-w-lg gap-3 text-sm">
        <div><dt class="text-slate-500">Nombre</dt><dd>{{ sesion.usuario.nombre }}</dd></div>
        <div><dt class="text-slate-500">Correo</dt><dd>{{ sesion.usuario.email }}</dd></div>
        <div><dt class="text-slate-500">Rol</dt><dd>{{ sesion.usuario.rol_display }}</dd></div>
        <div><dt class="text-slate-500">Empresa</dt><dd>{{ sesion.empresa_actual?.nombre || '—' }}</dd></div>
      </dl>
      <a routerLink="/clave" class="mt-6 inline-block text-sm text-sky-700">Cambiar contraseña</a>
    }
  `,
  imports: [RouterLink],
})
export class PerfilPage {
  readonly auth = inject(AuthService);
}
