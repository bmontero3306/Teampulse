import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { DashboardPage } from './dashboard.page';
import { HomePage } from './home.page';

const sesion = {
  usuario: { rol_display: 'Empleado', email: 'ana@demo.test' },
};

function renderPanel(payload: object): HTMLElement {
  const fixture = TestBed.createComponent(DashboardPage);
  const http = TestBed.inject(HttpTestingController);
  http.expectOne('/api/v1/dashboard/').flush(payload);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('Inicio y panel', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { sesion: () => sesion } },
      ],
    });
  });

  it('la portada repite los textos de home.html', () => {
    const fixture = TestBed.createComponent(HomePage);
    fixture.detectChanges();
    const html = fixture.nativeElement as HTMLElement;
    expect(html.textContent).toContain('El pulso de tu equipo');
    expect(html.textContent).toContain('Desempeño con evidencia, no con planillas sueltas');
    expect(html.textContent).toContain('Un flujo, tres voces');
    expect(html.textContent).toContain('Firma y rastro');
    expect(html.textContent).toContain('Reportes listos');
    expect(html.querySelectorAll('a[href="/login"]').length).toBe(2);
    expect(document.title).toBe('Inicio · TeamPulse');
  });

  it('el admin ve kpis en cero y la fecha con el formato de Django', () => {
    const html = renderPanel({
      ciclo_activo: {
        id: 1,
        nombre: 'Ciclo Q1',
        fecha_inicio: '2026-01-01',
        fecha_cierre: '2026-10-08',
      },
      kpis: { participantes: 5, auto: 4, supervisor: 3, firmadas: 2, sin_evaluador: 1 },
      pendientes: [],
      accesos_rapidos: [],
      equipo: null,
      empresas_plataforma: [],
      mostrar_pendientes: false,
      mostrar_equipo: false,
      mostrar_kpis: true,
      mostrar_empresas: false,
    });
    expect(html.querySelector('[data-widget="kpis"]')).not.toBeNull();
    expect(html.querySelector('[data-widget="pendientes"]')).toBeNull();
    expect(html.querySelector('[data-kpi="participantes"]')?.textContent).toContain('5');
    expect(html.textContent).toContain('Ciclo activo:');
    expect(html.textContent).toContain('Ciclo Q1');
    expect(html.textContent).toContain('1 Enero 2026');
    expect(html.textContent).toContain('8 Oct. 2026');
    expect(html.textContent).toContain('Vista de Empleado.');
    expect(html.textContent).toContain('Guías del proceso');
  });

  it('sin ciclo el admin muestra el vacío y los indicadores en cero', () => {
    const html = renderPanel({
      ciclo_activo: null,
      kpis: { participantes: 0, auto: 0, supervisor: 0, firmadas: 0, sin_evaluador: 0 },
      pendientes: [],
      accesos_rapidos: [],
      equipo: null,
      empresas_plataforma: [],
      mostrar_pendientes: false,
      mostrar_equipo: false,
      mostrar_kpis: true,
      mostrar_empresas: false,
    });
    expect(html.textContent).toContain('No hay ciclo activo.');
    expect(html.textContent).toContain('Los indicadores se van a completar cuando haya un ciclo activo.');
    expect(html.textContent).toContain('Sin ciclo');
    expect(html.querySelector('[data-kpi="sin_evaluador"]')?.textContent).toContain('0');
  });

  it('el empleado ve pendientes y accesos, sin kpis', () => {
    const html = renderPanel({
      ciclo_activo: { id: 1, nombre: 'Ciclo Q1', fecha_inicio: '2026-03-08', fecha_cierre: '2026-09-05' },
      kpis: null,
      pendientes: [
        {
          evaluacion_id: 9,
          accion: 'Completar autoevaluación',
          href: '/evaluaciones/9/autoevaluacion/',
          estado: 'autoevaluacion',
          estado_display: 'Autoevaluación',
          ciclo: 'Ciclo Q1',
        },
      ],
      accesos_rapidos: [
        { clave: 'mias', etiqueta: 'Mis evaluaciones', href: '/evaluaciones/mias' },
        { clave: 'auto', etiqueta: 'Autoevaluación', href: '/evaluaciones/9/autoevaluacion' },
      ],
      equipo: null,
      empresas_plataforma: [],
      mostrar_pendientes: true,
      mostrar_equipo: false,
      mostrar_kpis: false,
      mostrar_empresas: false,
    });
    expect(html.querySelector('[data-widget="pendientes"]')).not.toBeNull();
    expect(html.querySelector('[data-widget="kpis"]')).toBeNull();
    expect(html.querySelector('[data-acceso="mias"]')).not.toBeNull();
    expect(html.querySelector('[data-acceso="auto"]')).not.toBeNull();
    expect(html.textContent).toContain('ana@demo.test · Ciclo Q1');
    expect(html.textContent).toContain('Autoevaluación');
    expect(html.textContent).toContain('Completar autoevaluación');
    expect(html.textContent).toContain('5 Set. 2026');
  });

  it('el supervisor ve equipo, alertas y pendientes, en ese orden', () => {
    const html = renderPanel({
      ciclo_activo: { id: 1, nombre: 'Ciclo Q1', fecha_inicio: '2026-01-01', fecha_cierre: '2026-12-31' },
      kpis: null,
      pendientes: [],
      accesos_rapidos: [{ clave: 'mias', etiqueta: 'Mis evaluaciones', href: '/evaluaciones/mias' }],
      equipo: {
        total: 2,
        completitud: 50,
        alertas_sin_auto: [{ id: 3, evaluado: 'Mario Pendiente' }],
        evaluaciones: [
          { id: 3, evaluado: 'Mario Pendiente', estado: 'autoevaluacion', estado_display: 'Autoevaluación' },
          { id: 4, evaluado: 'Elena Lista', estado: 'evaluacion_supervisor', estado_display: 'Evaluación del supervisor' },
        ],
      },
      empresas_plataforma: [],
      mostrar_pendientes: true,
      mostrar_equipo: true,
      mostrar_kpis: false,
      mostrar_empresas: false,
    });
    const widgets = [...html.querySelectorAll('[data-widget]')].map((nodo) => nodo.getAttribute('data-widget'));
    expect(widgets).toEqual(['equipo', 'pendientes']);
    expect(html.querySelector('[data-equipo="completitud"]')?.textContent).toContain('50%');
    expect(html.querySelector('[data-alerta="sin-autoevaluacion"]')?.textContent).toContain('Mario Pendiente');
    expect(html.textContent).toContain('Sin pendientes');
  });

  it('el superadmin lista empresas y no avisa que falta el ciclo', () => {
    const html = renderPanel({
      ciclo_activo: null,
      kpis: null,
      pendientes: [],
      accesos_rapidos: [],
      equipo: null,
      empresas_plataforma: [
        { id: 1, nombre: 'Acme Industrial', estado: 'activa' },
        { id: 2, nombre: 'Taller Sur', estado: 'suspendida' },
      ],
      mostrar_pendientes: false,
      mostrar_equipo: false,
      mostrar_kpis: false,
      mostrar_empresas: true,
    });
    expect(html.querySelector('[data-widget="empresas"]')).not.toBeNull();
    expect(html.textContent).toContain('Acme Industrial');
    expect(html.textContent).toContain('Activa');
    expect(html.textContent).toContain('Suspendida');
    expect(html.textContent).not.toContain('No hay ciclo activo.');
  });

  it('el superadmin sin empresas ve el estado vacío', () => {
    const html = renderPanel({
      ciclo_activo: null,
      kpis: null,
      pendientes: [],
      accesos_rapidos: [],
      equipo: null,
      empresas_plataforma: [],
      mostrar_pendientes: false,
      mostrar_equipo: false,
      mostrar_kpis: false,
      mostrar_empresas: true,
    });
    expect(html.textContent).toContain('Todavía no hay empresas registradas');
    expect(html.textContent).toContain('Ir a empresas');
  });
});
