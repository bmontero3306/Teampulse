import { Component, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { combineLatest } from 'rxjs';

import { AuthService } from '../../core/auth.service';
import { TenantService } from '../../core/tenant.service';
import { AlertService } from '../../shared/alert.service';
import { mensajeError } from '../../shared/errores';
import { EmpresaSuspenderComponent } from './confirmar-suspender.component';
import { EmpresaDetalleComponent } from './detalle.component';
import { EmpresaApi } from './empresa.api';
import {
  ERRORES_VACIOS,
  Empresa,
  EmpresaPayload,
  ErroresEmpresa,
  VistaEmpresa,
  erroresEmpresa,
} from './empresa.model';
import { EmpresaFormComponent } from './form.component';
import { EmpresaListaComponent } from './lista.component';

export { SelectorEmpresaComponent } from './selector-empresa.component';

@Component({
  selector: 'app-empresas',
  imports: [EmpresaListaComponent, EmpresaFormComponent, EmpresaDetalleComponent, EmpresaSuspenderComponent],
  template: `
    @switch (vista()) {
      @case ('nueva') {
        <app-empresa-form
          titulo="Nueva empresa"
          [esFicha]="false"
          [empresa]="null"
          [errores]="errores()"
          (guardar)="guardar($event)"
        />
      }
      @case ('editar') {
        @if (empresa(); as actual) {
          <app-empresa-form
            titulo="Editar empresa"
            [esFicha]="esFicha()"
            [empresa]="actual"
            [errores]="errores()"
            (guardar)="guardar($event)"
          />
        }
      }
      @case ('detalle') {
        @if (empresa(); as actual) {
          <app-empresa-detalle [empresa]="actual" [rol]="rol()" (activar)="activar($event)" />
        }
      }
      @case ('suspender') {
        @if (empresa(); as actual) {
          <app-empresa-suspender [empresa]="actual" (confirmar)="confirmarSuspension()" />
        }
      }
      @default {
        <app-empresa-lista
          [empresas]="empresas()"
          [estadoFiltro]="estadoFiltro()"
          [cargando]="cargando()"
          (filtrar)="filtrar($event)"
          (activar)="activar($event)"
          (usar)="usar($event)"
        />
      }
    }
  `,
})
export class EmpresasPage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(EmpresaApi);
  private readonly alertas = inject(AlertService);
  private readonly auth = inject(AuthService);
  private readonly tenant = inject(TenantService);
  private readonly title = inject(Title);
  private token = 0;
  private ocupado = false;

  vista = signal<VistaEmpresa>('lista');
  empresas = signal<Empresa[]>([]);
  empresa = signal<Empresa | null>(null);
  estadoFiltro = signal('');
  cargando = signal(true);
  errores = signal<ErroresEmpresa>(ERRORES_VACIOS);
  readonly rol = computed(() => this.auth.sesion()?.usuario.rol ?? '');
  readonly esFicha = computed(() => this.vista() === 'editar' && this.rol() === 'admin_rrhh');

  constructor() {
    effect(() => {
      const vista = this.vista();
      const empresa = this.empresa();
      let pagina = 'Empresas';
      if (vista === 'nueva') {
        pagina = 'Nueva empresa';
      } else if (vista === 'editar') {
        pagina = 'Editar empresa';
      } else if (vista === 'detalle') {
        pagina = empresa?.nombre || 'Empresas';
      } else if (vista === 'suspender') {
        pagina = empresa ? `Suspender ${empresa.nombre}` : 'Suspender empresa';
      }
      this.title.setTitle(`${pagina} · TeamPulse`);
    });

    combineLatest([this.route.paramMap, this.route.queryParamMap])
      .pipe(takeUntilDestroyed())
      .subscribe(([, params]) => this.aplicar(params));
  }

  filtrar(estado: string): void {
    void this.router.navigate(['/empresas'], {
      queryParams: estado ? { estado } : {},
    });
  }

  guardar(valor: EmpresaPayload): void {
    if (this.ocupado) {
      return;
    }
    const editando = this.vista() === 'editar' ? this.empresa() : null;
    const cuerpo: Partial<EmpresaPayload> = this.esFicha()
      ? {
          nombre: valor.nombre,
          email_contacto: valor.email_contacto,
          telefono: valor.telefono,
          direccion: valor.direccion,
        }
      : valor;
    this.ocupado = true;
    const req = editando ? this.api.actualizar(editando.id, cuerpo) : this.api.crear(cuerpo);
    req.subscribe({
      next: (empresa) => {
        this.ocupado = false;
        this.alertas.success(
          editando ? 'La empresa se actualizó correctamente.' : 'La empresa se creó correctamente.',
        );
        void this.router.navigate(['/empresas', empresa.id]);
      },
      error: (err) => {
        this.ocupado = false;
        this.errores.set(erroresEmpresa(err));
      },
    });
  }

  activar(empresa: Empresa): void {
    if (this.ocupado) {
      return;
    }
    this.ocupado = true;
    this.api.activar(empresa.id).subscribe({
      next: (actualizada) => {
        this.ocupado = false;
        this.alertas.success('La empresa se activó correctamente.');
        if (this.vista() === 'detalle' && this.empresa()?.id === actualizada.id) {
          this.empresa.set({
            ...actualizada,
            cantidad_usuarios: this.empresa()?.cantidad_usuarios,
          });
          return;
        }
        void this.router.navigate(['/empresas', actualizada.id]);
      },
      error: (err) => {
        this.ocupado = false;
        this.alertas.error(mensajeError(err));
      },
    });
  }

  confirmarSuspension(): void {
    const empresa = this.empresa();
    if (!empresa || this.ocupado) {
      return;
    }
    this.ocupado = true;
    this.api.suspender(empresa.id).subscribe({
      next: () => {
        this.ocupado = false;
        this.alertas.success(
          'La empresa fue suspendida. Los datos se conservan; sus usuarios no podrán iniciar sesión.',
        );
        void this.router.navigate(['/empresas', empresa.id]);
      },
      error: (err) => {
        this.ocupado = false;
        this.alertas.error(mensajeError(err));
      },
    });
  }

  usar(empresa: Empresa): void {
    this.tenant.setEmpresa(empresa.id);
    this.auth.loadMe().subscribe(() => {
      this.alertas.success(`Contexto cambiado a ${empresa.nombre}.`);
    });
  }

  private aplicar(params: ParamMap): void {
    if (this.redirigirQuery(params)) {
      return;
    }
    const token = ++this.token;
    const { vista, id } = this.leerRuta();
    const estado = params.get('estado') ?? '';
    this.errores.set(ERRORES_VACIOS);
    this.vista.set(vista);
    this.estadoFiltro.set(vista === 'lista' ? estado : '');

    if (vista === 'lista') {
      this.empresa.set(null);
      this.empresas.set([]);
      this.cargando.set(true);
      this.api.listar(estado).subscribe({
          next: (lista) => {
            if (token !== this.token) {
              return;
            }
            this.empresas.set(lista);
            this.cargando.set(false);
          },
          error: (err) => {
            if (token !== this.token) {
              return;
            }
            this.empresas.set([]);
            this.cargando.set(false);
            this.alertas.error(mensajeError(err));
          },
        });
      return;
    }

    if (vista === 'nueva') {
      this.empresa.set(null);
      this.cargando.set(false);
      return;
    }

    if (!Number.isFinite(id) || id <= 0) {
      void this.router.navigate(['/empresas']);
      return;
    }

    this.cargando.set(true);
    this.api.obtener(id).subscribe({
      next: (empresa) => {
        if (token !== this.token) {
          return;
        }
        this.empresa.set(empresa);
        this.cargando.set(false);
      },
      error: (err) => {
        if (token !== this.token) {
          return;
        }
        this.cargando.set(false);
        this.alertas.error(mensajeError(err));
        void this.router.navigate(['/empresas']);
      },
    });
  }

  private leerRuta(): { vista: VistaEmpresa; id: number } {
    const partes = this.router.url.split('?')[0].split('/').filter(Boolean);
    if (partes[1] === 'nueva') {
      return { vista: 'nueva', id: 0 };
    }
    const id = partes[1] && /^\d+$/.test(partes[1]) ? Number(partes[1]) : 0;
    if (partes[2] === 'editar') {
      return { vista: 'editar', id };
    }
    if (partes[2] === 'suspender') {
      return { vista: 'suspender', id };
    }
    if (id) {
      return { vista: 'detalle', id };
    }
    return { vista: 'lista', id: 0 };
  }

  private redirigirQuery(params: ParamMap): boolean {
    const vista = params.get('vista');
    if (!vista) {
      return false;
    }
    const id = params.get('id');
    if (vista === 'nueva') {
      void this.router.navigate(['/empresas/nueva'], { replaceUrl: true });
      return true;
    }
    if (id && /^\d+$/.test(id)) {
      if (vista === 'editar' || vista === 'suspender') {
        void this.router.navigate(['/empresas', id, vista], { replaceUrl: true });
        return true;
      }
      if (vista === 'detalle') {
        void this.router.navigate(['/empresas', id], { replaceUrl: true });
        return true;
      }
    }
    return false;
  }
}
