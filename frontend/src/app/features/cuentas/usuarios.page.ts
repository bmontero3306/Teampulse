import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EMPTY, Observable, combineLatest, expand, forkJoin, reduce } from 'rxjs';

import { API } from '../../core/api';
import { Pagina, Usuario } from '../../core/models';
import {
  AYUDA_SUPERVISOR,
  CampoCuentaComponent,
  INPUT_CSS,
  MSG_EMAIL,
  MSG_OBLIGATORIO,
  MensajesCuentaComponent,
  type MensajeCuenta,
  SELECT_FILTRO_CSS,
  correoValido,
  erroresHttp,
} from './ui-cuenta';

interface AreaOpcion {
  id: number;
  nombre: string;
  activa?: boolean;
}

interface PuestoOpcion {
  id: number;
  nombre: string;
  activo?: boolean;
  puesto_superior: number | null;
}

interface AccionUsuario {
  id: number;
  tipo: 'desactivar' | 'bloquear' | 'reset-clave';
  titulo: string;
  mensaje: string;
  confirmacion: string;
  peligro: boolean;
}

@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule, RouterLink, CampoCuentaComponent, MensajesCuentaComponent],
  template: `
    @if (vista() === 'lista') {
      <section>
        <app-mensajes-cuenta [mensajes]="mensajes()" />
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 class="text-2xl font-semibold tracking-tight text-slate-900">Usuarios</h1>
            <p class="mt-1 text-sm text-slate-600">Altas, roles y estado de las cuentas de la empresa.</p>
          </div>
          <a
            routerLink="/usuarios/nuevo"
            class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
          >
            Nuevo usuario
          </a>
        </div>

        <form class="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-4" (submit)="$event.preventDefault(); filtrar()">
          <div>
            <label for="filtro-rol" class="mb-1 block text-xs font-medium text-slate-600">Rol</label>
            <select id="filtro-rol" name="rol" [formControl]="filtroRol" [class]="selectFiltro">
              <option value="">Todos</option>
              @for (rol of rolesFiltro; track rol.value) {
                <option [value]="rol.value">{{ rol.label }}</option>
              }
            </select>
          </div>
          <div>
            <label for="filtro-activo" class="mb-1 block text-xs font-medium text-slate-600">Activo</label>
            <select id="filtro-activo" name="activo" [formControl]="filtroActivo" [class]="selectFiltro">
              <option value="">Todos</option>
              <option value="1">Activos</option>
              <option value="0">Inactivos</option>
            </select>
          </div>
          <div>
            <label for="filtro-area" class="mb-1 block text-xs font-medium text-slate-600">Área</label>
            <select id="filtro-area" name="area" [formControl]="filtroArea" [class]="selectFiltro">
              <option value="">Todas</option>
              @for (area of areas(); track area.id) {
                <option [value]="area.id">{{ area.nombre }}</option>
              }
            </select>
          </div>
          <div class="flex items-end">
            <button type="submit" class="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              Filtrar
            </button>
          </div>
        </form>

        <div class="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th class="px-4 py-3">Nombre</th>
                <th class="px-4 py-3">Correo</th>
                <th class="px-4 py-3">Rol</th>
                <th class="px-4 py-3">Área</th>
                <th class="px-4 py-3">Estado</th>
                <th class="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (item of usuarios(); track item.id) {
                <tr class="hover:bg-slate-50">
                  <td class="px-4 py-3 font-medium text-slate-900">{{ nombreLista(item) }}</td>
                  <td class="px-4 py-3 text-slate-600">{{ item.email }}</td>
                  <td class="px-4 py-3 capitalize text-slate-700">{{ item.rol_display }}</td>
                  <td class="px-4 py-3 text-slate-600">{{ item.area_nombre || '—' }}</td>
                  <td class="px-4 py-3">
                    @if (item.bloqueado) {
                      <span class="inline-flex rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">Bloqueado</span>
                    } @else if (item.is_active) {
                      <span class="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">Activo</span>
                    } @else {
                      <span class="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Inactivo</span>
                    }
                  </td>
                  <td class="px-4 py-3 text-right whitespace-nowrap">
                    <a [routerLink]="['/usuarios', item.id, 'editar']" class="font-medium text-sky-700 hover:text-sky-800">Editar</a>
                    <a [routerLink]="['/usuarios', item.id, 'desactivar']" class="ml-3 font-medium text-slate-600 hover:text-slate-900">Desactivar</a>
                    <a [routerLink]="['/usuarios', item.id, 'bloquear']" class="ml-3 font-medium text-red-700 hover:text-red-800">Bloquear</a>
                    <a [routerLink]="['/usuarios', item.id, 'reset-clave']" class="ml-3 font-medium text-slate-600 hover:text-slate-900">Reset clave</a>
                  </td>
                </tr>
              } @empty {
                @if (listo()) {
                  <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-slate-500">No hay usuarios para mostrar.</td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
      </section>
    } @else if (vista() === 'form') {
      <section class="mx-auto max-w-2xl">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
          {{ editando() ? 'Editar usuario' : 'Nuevo usuario' }}
        </h1>
        <p class="mt-1 text-sm text-slate-600">
          @if (editando()) {
            Los cambios se notifican a la persona.
          } @else {
            Al crear la cuenta se genera una contraseña temporal y se envía una notificación.
          }
        </p>

        <form class="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" [formGroup]="form" (ngSubmit)="guardar()">
          <app-mensajes-cuenta [general]="general()" />
          <div class="grid gap-4 sm:grid-cols-2">
            <app-campo-cuenta id="id_first_name" label="Nombre" [required]="true" [error]="error('first_name')">
              <input id="id_first_name" name="first_name" type="text" maxlength="150" formControlName="first_name" [class]="inputCss" />
            </app-campo-cuenta>
            <app-campo-cuenta id="id_last_name" label="Apellido" [required]="true" [error]="error('last_name')">
              <input id="id_last_name" name="last_name" type="text" maxlength="150" formControlName="last_name" [class]="inputCss" />
            </app-campo-cuenta>
          </div>
          <app-campo-cuenta id="id_email" label="Correo electrónico" [required]="true" [error]="error('email')">
            <input id="id_email" name="email" type="email" maxlength="254" autocomplete="email" formControlName="email" [class]="inputCss" />
          </app-campo-cuenta>
          <app-campo-cuenta id="id_dni" label="DNI" [error]="error('dni')">
            <input id="id_dni" name="dni" type="text" maxlength="20" formControlName="dni" [class]="inputCss" />
          </app-campo-cuenta>
          <app-campo-cuenta id="id_rol" label="Rol" [required]="true" [error]="error('rol')">
            <select id="id_rol" name="rol" formControlName="rol" [class]="inputCss">
              @for (rol of rolesForm; track rol.value) {
                <option [value]="rol.value">{{ rol.label }}</option>
              }
            </select>
          </app-campo-cuenta>
          <app-campo-cuenta id="id_area" label="Área" [error]="error('area')">
            <select id="id_area" name="area" formControlName="area" [class]="inputCss">
              <option value="">---------</option>
              @for (area of areasFormulario(); track area.id) {
                <option [value]="area.id">{{ area.nombre }}</option>
              }
            </select>
          </app-campo-cuenta>
          <app-campo-cuenta id="id_puesto" label="Puesto" [error]="error('puesto')">
            <select id="id_puesto" name="puesto" formControlName="puesto" [class]="inputCss" (change)="alCambiarPuesto()">
              <option value="">---------</option>
              @for (puesto of puestosFormulario(); track puesto.id) {
                <option [value]="puesto.id">{{ puesto.nombre }}</option>
              }
            </select>
          </app-campo-cuenta>
          <app-campo-cuenta id="id_supervisor" label="Supervisor" [help]="ayudaSupervisor" [error]="error('supervisor')">
            <select id="id_supervisor" name="supervisor" formControlName="supervisor" [class]="inputCss">
              <option value="">---------</option>
              @for (persona of supervisores(); track persona.id) {
                <option [value]="persona.id">{{ persona.email }}</option>
              }
            </select>
          </app-campo-cuenta>
          @if (editando()) {
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input id="id_is_active" type="checkbox" formControlName="is_active" /> Activo
            </label>
            <label class="flex items-center gap-2 text-sm text-slate-700">
              <input id="id_bloqueado" type="checkbox" formControlName="bloqueado" /> Bloqueado
            </label>
          }
          <div class="flex items-center gap-3 pt-2">
            <button type="submit" class="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700">
              Guardar
            </button>
            <a routerLink="/usuarios" class="text-sm font-medium text-slate-600 hover:text-slate-900">Cancelar</a>
          </div>
        </form>
      </section>
    } @else if (vista() === 'confirmar') {
      @if (accion(); as actual) {
      <section class="mx-auto max-w-lg">
        <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ actual.titulo }}</h1>
          <p class="mt-3 text-sm text-slate-600">{{ actual.mensaje }}</p>
          <form class="mt-6 flex items-center gap-3" (submit)="$event.preventDefault(); confirmar()">
            <button
              type="submit"
              [class]="
                'rounded-lg px-4 py-2 text-sm font-semibold text-white ' +
                (actual.peligro ? 'bg-red-600 hover:bg-red-700' : 'bg-sky-600 hover:bg-sky-700')
              "
            >
              {{ actual.confirmacion }}
            </button>
            <a routerLink="/usuarios" class="text-sm font-medium text-slate-600 hover:text-slate-900">Cancelar</a>
          </form>
        </div>
      </section>
      }
    }
  `,
})
export class UsuariosPage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly title = inject(Title);
  private token = 0;
  readonly inputCss = INPUT_CSS;
  readonly selectFiltro = SELECT_FILTRO_CSS;
  readonly ayudaSupervisor = AYUDA_SUPERVISOR;
  readonly rolesFiltro = [
    { value: 'superadmin', label: 'Superadmin' },
    { value: 'admin_rrhh', label: 'Admin RRHH' },
    { value: 'supervisor', label: 'Supervisor' },
    { value: 'empleado', label: 'Empleado' },
  ];
  readonly rolesForm = [
    { value: 'admin_rrhh', label: 'Admin RRHH' },
    { value: 'supervisor', label: 'Supervisor' },
    { value: 'empleado', label: 'Empleado' },
  ];

  vista = signal<'lista' | 'form' | 'confirmar'>('lista');
  usuarios = signal<Usuario[]>([]);
  areas = signal<AreaOpcion[]>([]);
  puestos = signal<PuestoOpcion[]>([]);
  activos = signal<Usuario[]>([]);
  editando = signal<number | null>(null);
  accion = signal<AccionUsuario | null>(null);
  mensajes = signal<MensajeCuenta[]>([]);
  listo = signal(false);
  errores = signal<Record<string, string>>({});
  general = signal('');

  filtroRol = new FormControl('', { nonNullable: true });
  filtroActivo = new FormControl('', { nonNullable: true });
  filtroArea = new FormControl('', { nonNullable: true });
  form = new FormGroup({
    first_name: new FormControl('', { nonNullable: true }),
    last_name: new FormControl('', { nonNullable: true }),
    email: new FormControl('', { nonNullable: true }),
    dni: new FormControl('', { nonNullable: true }),
    rol: new FormControl('empleado', { nonNullable: true }),
    area: new FormControl('', { nonNullable: true }),
    puesto: new FormControl('', { nonNullable: true }),
    supervisor: new FormControl('', { nonNullable: true }),
    is_active: new FormControl(true, { nonNullable: true }),
    bloqueado: new FormControl(false, { nonNullable: true }),
  });

  areasFormulario = computed(() => {
    const lista = this.areas();
    return this.editando() ? lista : lista.filter((area) => area.activa !== false);
  });

  puestosFormulario = computed(() => {
    const lista = this.puestos();
    return this.editando() ? lista : lista.filter((puesto) => puesto.activo !== false);
  });

  supervisores = computed(() => {
    const propio = this.editando();
    return this.activos().filter((usuario) => usuario.id !== propio && usuario.is_active !== false);
  });

  mapaSupervisor = computed(() => {
    const ocupantes = new Map<number, number>();
    for (const usuario of this.activos()) {
      if (usuario.puesto) ocupantes.set(usuario.puesto, usuario.id);
    }
    const mapa: Record<string, number> = {};
    for (const puesto of this.puestos()) {
      if (puesto.puesto_superior && ocupantes.has(puesto.puesto_superior)) {
        mapa[String(puesto.id)] = ocupantes.get(puesto.puesto_superior)!;
      }
    }
    return mapa;
  });

  constructor() {
    this.cargarCatalogos();
    combineLatest([this.route.paramMap, this.route.url])
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.aplicarRuta());
  }

  error(campo: string): string {
    return this.errores()[campo] ?? '';
  }

  nombreLista(item: Usuario): string {
    const completo = `${item.first_name} ${item.last_name}`.trim();
    return completo || item.email;
  }

  filtrar(): void {
    this.cargar();
  }

  cargar(): void {
    const params: Record<string, string> = { page_size: '50' };
    if (this.filtroRol.value) params['rol'] = this.filtroRol.value;
    if (this.filtroActivo.value) params['activo'] = this.filtroActivo.value;
    if (this.filtroArea.value) params['area'] = this.filtroArea.value;
    this.http.get<Pagina<Usuario>>(`${API}/usuarios/`, { params }).subscribe({
      next: (pagina) => {
        this.usuarios.set(pagina.results);
        this.listo.set(true);
      },
      error: (err) => {
        this.listo.set(true);
        this.mensajes.set([{ tipo: 'error', texto: erroresHttp(err).general || 'No se pudo completar la operación.' }]);
      },
    });
  }

  private aplicarRuta(): void {
    const token = ++this.token;
    const partes = this.router.url.split('?')[0].split('/').filter(Boolean);
    const id = partes[1] && /^\d+$/.test(partes[1]) ? Number(partes[1]) : null;
    const accion = partes[1] === 'nuevo' ? 'nuevo' : (partes[2] ?? '');
    this.errores.set({});
    this.general.set('');
    this.accion.set(null);

    if (accion === 'nuevo') {
      this.editando.set(null);
      this.mensajes.set([]);
      this.form.reset({
        first_name: '',
        last_name: '',
        email: '',
        dni: '',
        rol: 'empleado',
        area: '',
        puesto: '',
        supervisor: '',
        is_active: true,
        bloqueado: false,
      });
      this.vista.set('form');
      this.title.setTitle('Nuevo usuario · TeamPulse');
      return;
    }

    if (id && accion === 'editar') {
      this.vista.set('form');
      this.title.setTitle('Editar usuario · TeamPulse');
      this.cargarUsuario(token, id, (item) => this.rellenar(item));
      return;
    }

    if (id && (accion === 'desactivar' || accion === 'bloquear' || accion === 'reset-clave')) {
      this.vista.set('confirmar');
      this.cargarUsuario(token, id, (item) => this.pedir(accion, item));
      return;
    }

    this.editando.set(null);
    this.vista.set('lista');
    this.title.setTitle('Usuarios · TeamPulse');
    const state = window.history.state as { mensajes?: MensajeCuenta[] };
    const mensajes = Array.isArray(state?.mensajes) ? state.mensajes : [];
    this.mensajes.set(mensajes);
    if (mensajes.length) {
      history.replaceState({ ...state, mensajes: undefined }, '');
    }
    this.cargar();
  }

  private rellenar(item: Usuario): void {
    this.editando.set(item.id);
    this.mensajes.set([]);
    this.form.reset({
      first_name: item.first_name,
      last_name: item.last_name,
      email: item.email,
      dni: item.dni ?? '',
      rol: item.rol,
      area: item.area ? String(item.area) : '',
      puesto: item.puesto ? String(item.puesto) : '',
      supervisor: item.supervisor ? String(item.supervisor) : '',
      is_active: item.is_active !== false,
      bloqueado: Boolean(item.bloqueado),
    });
  }

  private cargarUsuario(token: number, id: number, listo: (item: Usuario) => void): void {
    this.http.get<Usuario>(`${API}/usuarios/${id}/`).subscribe({
      next: (item) => {
        if (token !== this.token) {
          return;
        }
        listo(item);
      },
      error: (err) => {
        if (token !== this.token) {
          return;
        }
        this.mensajes.set([{ tipo: 'error', texto: erroresHttp(err).general || 'No se pudo completar la operación.' }]);
        void this.router.navigate(['/usuarios'], { state: { mensajes: this.mensajes() } });
      },
    });
  }

  alCambiarPuesto(): void {
    const supervisorId = this.mapaSupervisor()[this.form.controls.puesto.value];
    if (supervisorId) this.form.controls.supervisor.setValue(String(supervisorId));
  }

  guardar(): void {
    const raw = this.form.getRawValue();
    const errores: Record<string, string> = {};
    if (!raw.first_name.trim()) errores['first_name'] = MSG_OBLIGATORIO;
    if (!raw.last_name.trim()) errores['last_name'] = MSG_OBLIGATORIO;
    if (!raw.email.trim()) errores['email'] = MSG_OBLIGATORIO;
    else if (!correoValido(raw.email.trim())) errores['email'] = MSG_EMAIL;
    if (!raw.rol) errores['rol'] = MSG_OBLIGATORIO;
    this.errores.set(errores);
    this.general.set('');
    if (Object.keys(errores).length) return;

    const id = this.editando();
    const body: Record<string, unknown> = {
      first_name: raw.first_name.trim(),
      last_name: raw.last_name.trim(),
      email: raw.email.trim(),
      dni: raw.dni.trim(),
      rol: raw.rol,
      area: raw.area ? Number(raw.area) : null,
      puesto: raw.puesto ? Number(raw.puesto) : null,
      supervisor: raw.supervisor ? Number(raw.supervisor) : null,
    };
    if (id) {
      body['is_active'] = raw.is_active;
      body['bloqueado'] = raw.bloqueado;
    }
    const req = id
      ? this.http.patch<Usuario & { clave_temporal?: string }>(`${API}/usuarios/${id}/`, body)
      : this.http.post<Usuario & { clave_temporal?: string }>(`${API}/usuarios/`, body);
    req.subscribe({
      next: (usuario) => {
        const texto = id
          ? 'Usuario actualizado. Se envió notificación al usuario.'
          : `Usuario creado. Se envió notificación al usuario. Contraseña temporal: ${usuario.clave_temporal ?? ''}`;
        void this.router.navigate(['/usuarios'], { state: { mensajes: [{ tipo: 'success', texto }] } });
      },
      error: (err) => {
        const parsed = erroresHttp(err);
        this.errores.set(parsed.campos);
        this.general.set(parsed.general);
      },
    });
  }

  pedir(tipo: AccionUsuario['tipo'], item: Usuario): void {
    const textos: Record<AccionUsuario['tipo'], Omit<AccionUsuario, 'id' | 'tipo'>> = {
      desactivar: {
        titulo: 'Desactivar usuario',
        mensaje: `¿Desactivar a ${item.email}? No podrá iniciar sesión.`,
        confirmacion: 'Desactivar',
        peligro: true,
      },
      bloquear: {
        titulo: 'Bloquear usuario',
        mensaje: `¿Bloquear a ${item.email}? No podrá iniciar sesión hasta que se desbloquee.`,
        confirmacion: 'Bloquear',
        peligro: true,
      },
      'reset-clave': {
        titulo: 'Restablecer contraseña',
        mensaje: `¿Generar una contraseña temporal para ${item.email}?`,
        confirmacion: 'Restablecer clave',
        peligro: false,
      },
    };
    this.mensajes.set([]);
    this.accion.set({ id: item.id, tipo, ...textos[tipo] });
    this.vista.set('confirmar');
    this.title.setTitle(`${textos[tipo].titulo} · TeamPulse`);
  }

  confirmar(): void {
    const actual = this.accion();
    if (!actual) return;
    this.http
      .post<Usuario & { clave_temporal?: string }>(`${API}/usuarios/${actual.id}/${actual.tipo}/`, {})
      .subscribe({
        next: (resp) => {
          const texto =
            actual.tipo === 'desactivar'
              ? 'Usuario desactivado. Se envió notificación al usuario.'
              : actual.tipo === 'bloquear'
                ? 'Usuario bloqueado. Se envió notificación al usuario.'
                : `Se restableció la clave. Se envió notificación al usuario. Contraseña temporal: ${resp.clave_temporal ?? ''}`;
          void this.router.navigate(['/usuarios'], { state: { mensajes: [{ tipo: 'success', texto }] } });
        },
        error: (err) => {
          const parsed = erroresHttp(err);
          void this.router.navigate(['/usuarios'], {
            state: { mensajes: [{ tipo: 'error', texto: parsed.general || 'No se pudo completar la operación.' }] },
          });
        },
      });
  }

  private cargarCatalogos(): void {
    forkJoin({
      areas: this.paginas<AreaOpcion>(`${API}/areas/?page_size=100`),
      puestos: this.paginas<PuestoOpcion>(`${API}/puestos/?page_size=100`),
      activos: this.paginas<Usuario>(`${API}/usuarios/?activo=1&page_size=100`),
    }).subscribe({
      next: ({ areas, puestos, activos }) => {
        this.areas.set(areas);
        this.puestos.set(puestos);
        this.activos.set(activos);
      },
    });
  }

  private paginas<T>(url: string): Observable<T[]> {
    return this.http.get<Pagina<T>>(url).pipe(
      expand((pagina) => (pagina.next ? this.http.get<Pagina<T>>(this.ruta(pagina.next)) : EMPTY)),
      reduce((acc, pagina) => acc.concat(pagina.results), [] as T[]),
    );
  }

  private ruta(url: string): string {
    if (url.startsWith('http')) {
      const absoluta = new URL(url);
      return `${absoluta.pathname}${absoluta.search}`;
    }
    return url;
  }
}
