import { Routes } from '@angular/router';

import { authGuard, claveGuard, guestGuard, mustChangePasswordGuard, rolGuard } from './core/guards';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./features/cuentas/auth.pages').then((m) => m.HomePage) },
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
        canActivate: [rolGuard],
        data: { roles: ['superadmin'] },
        loadComponent: () => import('./features/empresas/empresas.page').then((m) => m.EmpresasPage),
      },
      {
        path: 'usuarios',
        canActivate: [rolGuard],
        data: { roles: ['superadmin', 'admin_rrhh'] },
        loadComponent: () => import('./features/cuentas/usuarios.page').then((m) => m.UsuariosPage),
      },
      {
        path: 'organizacion',
        loadComponent: () => import('./features/organizacion/organizacion.page').then((m) => m.OrganizacionPage),
      },
      {
        path: 'evaluaciones/plantillas',
        loadComponent: () => import('./features/evaluaciones/plantillas-ciclos.page').then((m) => m.PlantillasPage),
      },
      {
        path: 'evaluaciones/ciclos',
        loadComponent: () => import('./features/evaluaciones/plantillas-ciclos.page').then((m) => m.CiclosPage),
      },
      {
        path: 'evaluaciones/ciclos/:id',
        loadComponent: () => import('./features/evaluaciones/plantillas-ciclos.page').then((m) => m.CicloDetallePage),
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
        loadComponent: () => import('./features/resto/resto.pages').then((m) => m.NotificacionesPage),
      },
      {
        path: 'reportes/iso',
        canActivate: [rolGuard],
        data: { roles: ['superadmin', 'admin_rrhh'] },
        loadComponent: () => import('./features/resto/resto.pages').then((m) => m.ReportesPage),
      },
      {
        path: 'auditoria',
        canActivate: [rolGuard],
        data: { roles: ['superadmin', 'admin_rrhh'] },
        loadComponent: () => import('./features/resto/resto.pages').then((m) => m.AuditoriaPage),
      },
      {
        path: 'ayuda',
        loadComponent: () => import('./features/resto/resto.pages').then((m) => m.AyudaPage),
      },
      {
        path: 'ayuda/:slug',
        loadComponent: () => import('./features/resto/resto.pages').then((m) => m.AyudaPaginaPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
