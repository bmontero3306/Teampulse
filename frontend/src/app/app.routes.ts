import { Routes } from '@angular/router';

import { authGuard, claveGuard, guestGuard, mustChangePasswordGuard, rolGuard } from './core/guards';
import { PublicLayoutComponent } from './layout/public-layout.component';
import { ShellComponent } from './layout/shell.component';

const rolesSuperadmin = { canActivate: [rolGuard], data: { roles: ['superadmin'] } };
const rolesRrhh = { canActivate: [rolGuard], data: { roles: ['superadmin', 'admin_rrhh'] } };

export const routes: Routes = [
  {
    path: '',
    component: PublicLayoutComponent,
    children: [
      { path: '', loadComponent: () => import('./features/panel/home.page').then((m) => m.HomePage) },
    ],
  },
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.LoginPage),
  },
  {
    path: 'recuperar',
    loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.RecuperarPage),
  },
  {
    path: 'recuperar/:uid/:token',
    loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.ResetConfirmPage),
  },
  {
    path: 'clave',
    canActivate: [claveGuard],
    loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.ClavePage),
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard, mustChangePasswordGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./features/panel/dashboard.page').then((m) => m.DashboardPage),
      },
      {
        path: 'perfil',
        loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.PerfilPage),
      },
      {
        path: 'empresas',
        ...rolesSuperadmin,
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'empresas/nueva',
        ...rolesSuperadmin,
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'empresas/:id/editar',
        ...rolesSuperadmin,
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'empresas/:id/suspender',
        ...rolesSuperadmin,
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'empresas/:id',
        ...rolesSuperadmin,
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'usuarios',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'usuarios/nuevo',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'usuarios/:id/editar',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'usuarios/:id/desactivar',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'usuarios/:id/bloquear',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'usuarios/:id/reset-clave',
        ...rolesRrhh,
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'organizacion',
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/organigrama',
        redirectTo: '/organizacion',
        pathMatch: 'full',
      },
      {
        path: 'organizacion/puestos',
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/puestos/nuevo',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/puestos/:id/editar',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/areas',
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/areas/nueva',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/areas/:id/editar',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/competencias',
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/competencias/nueva',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'organizacion/competencias/:id/editar',
        ...rolesRrhh,
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'evaluaciones/plantillas',
        loadComponent: () => import('./features/evaluaciones/plantillas-ciclos.page').then((m) => m.PlantillasPage),
      },
      {
        path: 'evaluaciones/plantillas/nueva',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/plantilla-form.page').then((m) => m.PlantillaFormPage),
      },
      {
        path: 'evaluaciones/plantillas/:id/editar',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/plantilla-form.page').then((m) => m.PlantillaFormPage),
      },
      {
        path: 'evaluaciones/ciclos',
        loadComponent: () => import('./features/evaluaciones/plantillas-ciclos.page').then((m) => m.CiclosPage),
      },
      {
        path: 'evaluaciones/ciclos/nuevo',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/ciclo-form.page').then((m) => m.CicloFormPage),
      },
      {
        path: 'evaluaciones/ciclos/:id/reprogramar',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/ciclo-detalle.page').then((m) => m.CicloDetallePage),
      },
      {
        path: 'evaluaciones/ciclos/:id/activar',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/ciclo-detalle.page').then((m) => m.CicloDetallePage),
      },
      {
        path: 'evaluaciones/ciclos/:id/pausar',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/ciclo-detalle.page').then((m) => m.CicloDetallePage),
      },
      {
        path: 'evaluaciones/ciclos/:id/cancelar',
        ...rolesRrhh,
        loadComponent: () => import('./features/evaluaciones/ciclo-detalle.page').then((m) => m.CicloDetallePage),
      },
      {
        path: 'evaluaciones/ciclos/:id',
        loadComponent: () => import('./features/evaluaciones/ciclo-detalle.page').then((m) => m.CicloDetallePage),
      },
      {
        path: 'evaluaciones/mias',
        loadComponent: () => import('./features/evaluaciones/flujo.page').then((m) => m.MiasPage),
      },
      {
        path: 'evaluaciones/equipo',
        canActivate: [rolGuard],
        data: { roles: ['supervisor'] },
        loadComponent: () => import('./features/evaluaciones/flujo.page').then((m) => m.EquipoPage),
      },
      {
        path: 'evaluaciones/:id/autoevaluacion',
        data: { modo: 'auto' },
        loadComponent: () => import('./features/evaluaciones/flujo.page').then((m) => m.FlujoPage),
      },
      {
        path: 'evaluaciones/:id/supervisar',
        data: { modo: 'supervisar' },
        loadComponent: () => import('./features/evaluaciones/flujo.page').then((m) => m.FlujoPage),
      },
      {
        path: 'evaluaciones/:id/resultado',
        data: { modo: 'resultado' },
        loadComponent: () => import('./features/evaluaciones/flujo.page').then((m) => m.FlujoPage),
      },
      {
        path: 'notificaciones',
        loadComponent: () => import('./features/resto/notificaciones.page').then((m) => m.NotificacionesPage),
      },
      {
        path: 'reportes/iso',
        ...rolesRrhh,
        loadComponent: () => import('./features/resto/reportes.page').then((m) => m.ReportesPage),
      },
      {
        path: 'auditoria',
        ...rolesRrhh,
        loadComponent: () => import('./features/resto/auditoria.page').then((m) => m.AuditoriaPage),
      },
      {
        path: 'ayuda',
        loadComponent: () => import('./features/ayuda/ayuda.page').then((m) => m.AyudaPage),
      },
      {
        path: 'ayuda',
        loadComponent: () => import('./features/ayuda/ayuda-layout').then((m) => m.AyudaLayoutComponent),
        children: [
          {
            path: ':slug',
            loadComponent: () => import('./features/ayuda/ayuda-pagina.page').then((m) => m.AyudaPaginaPage),
          },
        ],
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
