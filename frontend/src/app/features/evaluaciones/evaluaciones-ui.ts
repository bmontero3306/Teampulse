import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, expand, reduce } from 'rxjs';

import { Pagina } from '../../core/models';

export const INPUT_CSS =
  'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500';

export const TEXTAREA_CSS = `${INPUT_CSS} min-h-24`;

export const CHECKBOX_CSS = 'h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500';

export const TIPOS_PLANTILLA: { value: string; label: string }[] = [
  { value: 'tecnica', label: 'Técnica' },
  { value: 'actitudinal', label: 'Actitudinal' },
  { value: 'objetivos', label: 'Objetivos' },
  { value: 'mixta', label: 'Mixta' },
];

export const TIPOS_COMPETENCIA: { value: string; label: string }[] = [
  { value: 'tecnica', label: 'Técnica' },
  { value: 'actitudinal', label: 'Actitudinal' },
  { value: 'objetivo', label: 'Objetivo' },
  { value: 'otra', label: 'Otra' },
];

export interface CriterioApi {
  id?: number;
  competencia: number;
  competencia_nombre?: string;
  categoria: string;
  tipo_item: string;
  orden: number;
  escala_min: number;
  escala_max: number;
  ponderacion: string | number;
  comentario_empleado_obligatorio: boolean;
  comentario_supervisor_obligatorio: boolean;
}

export interface PlantillaApi {
  id: number;
  nombre: string;
  tipo: string;
  descripcion: string;
  activa: boolean;
  puestos: number[];
  puestos_nombres: string[];
  criterios: CriterioApi[];
}

export interface CriterioEdicion {
  key: number;
  id?: number;
  competencia: number | null;
  competenciaNombre: string;
  categoria: string;
  tipo_item: 'escala' | 'texto';
  orden: string;
  escala_min: string;
  escala_max: string;
  ponderacion: string;
  devEmpleado: boolean;
  devSupervisor: boolean;
  abierto: boolean;
  quitar: boolean;
  errorGeneral: string;
  errores: Record<string, string[]>;
}

export interface CompetenciaOpcion {
  id: number;
  nombre: string;
  descripcion: string;
  tipo: string;
  activa: boolean;
}

export interface PuestoOpcion {
  id: number;
  nombre: string;
  area: string;
  activo: boolean;
}

export interface AreaOpcion {
  id: number;
  nombre: string;
  activa: boolean;
}

export interface CicloApi {
  id: number;
  nombre: string;
  fecha_inicio: string;
  fecha_cierre: string;
  estado: string;
  plantilla_default: number;
  plantilla_nombre: string;
  areas: number[];
  criterios_generales: string;
  total_evals?: number;
  sin_evaluador_count?: number;
}

export interface PersonaBreve {
  id: number;
  email: string;
  nombre: string;
  first_name: string;
  last_name: string;
}

export interface ParticipanteApi {
  id: number;
  estado: string;
  estado_display: string;
  en_borrador?: boolean;
  con_observacion?: boolean;
  evaluado: PersonaBreve | null;
  evaluador: PersonaBreve | null;
  puesto_nombre: string;
  sin_evaluador: boolean;
  comparacion_revelada: boolean;
}

export interface CandidatoEvaluador {
  id: number;
  nombre: string;
  email: string;
  rol: string;
}

export interface ErroresApi {
  generales: string[];
  campos: Record<string, string[]>;
  criteriosGenerales: string[];
  filas: Record<number, { generales: string[]; campos: Record<string, string[]> }>;
}

export function erroresVacios(): ErroresApi {
  return { generales: [], campos: {}, criteriosGenerales: [], filas: {} };
}

export function esGestion(rol: string | undefined): boolean {
  return rol === 'superadmin' || rol === 'admin_rrhh';
}

export function normalizar(valor: string): string {
  return valor.trim().toLowerCase();
}

export function fechaCorta(iso: string | null | undefined): string {
  if (!iso) {
    return '';
  }
  const [anio, mes, dia] = iso.slice(0, 10).split('-');
  if (!anio || !mes || !dia) {
    return iso;
  }
  return `${dia}/${mes}/${anio}`;
}

export function etiquetaPuesto(puesto: { nombre: string; area: string }): string {
  return puesto.area ? `${puesto.nombre} · ${puesto.area}` : puesto.nombre;
}

export function textoDevolucion(empleado: boolean, supervisor: boolean): string {
  if (empleado && supervisor) {
    return 'Empleado y supervisor';
  }
  if (empleado) {
    return 'Solo empleado';
  }
  if (supervisor) {
    return 'Solo supervisor';
  }
  return 'Opcional';
}

export function textoTipoItem(tipo: string): string {
  return tipo === 'texto' ? 'Solo texto' : 'Escala numérica';
}

export function filaVacia(key: number): CriterioEdicion {
  return {
    key,
    competencia: null,
    competenciaNombre: '',
    categoria: '',
    tipo_item: 'escala',
    orden: '',
    escala_min: '1',
    escala_max: '5',
    ponderacion: '0',
    devEmpleado: true,
    devSupervisor: true,
    abierto: false,
    quitar: false,
    errorGeneral: '',
    errores: {},
  };
}

export function filaDesdeApi(criterio: CriterioApi, key: number): CriterioEdicion {
  return {
    key,
    id: criterio.id,
    competencia: criterio.competencia,
    competenciaNombre: criterio.competencia_nombre ?? '',
    categoria: criterio.categoria ?? '',
    tipo_item: criterio.tipo_item === 'texto' ? 'texto' : 'escala',
    orden: criterio.orden == null ? '' : String(criterio.orden),
    escala_min: String(criterio.escala_min ?? 1),
    escala_max: String(criterio.escala_max ?? 5),
    ponderacion: criterio.ponderacion == null ? '0' : String(criterio.ponderacion),
    devEmpleado: criterio.comentario_empleado_obligatorio,
    devSupervisor: criterio.comentario_supervisor_obligatorio,
    abierto: false,
    quitar: false,
    errorGeneral: '',
    errores: {},
  };
}

const AUTO = new Set([
  'evaluacion_supervisor',
  'pendiente_reunion',
  'pendiente_conformidad',
  'cerrada',
]);

const SUPERVISOR = new Set(['pendiente_reunion', 'pendiente_conformidad', 'cerrada']);

const FIRMADAS = new Set(['cerrada']);

export interface ProgresoCiclo {
  total: number;
  auto: number;
  supervisor: number;
  firmadas: number;
  sinEvaluador: number;
}

export function progresoCiclo(participantes: ParticipanteApi[]): ProgresoCiclo {
  return {
    total: participantes.length,
    auto: participantes.filter((item) => AUTO.has(item.estado)).length,
    supervisor: participantes.filter((item) => SUPERVISOR.has(item.estado)).length,
    firmadas: participantes.filter((item) => FIRMADAS.has(item.estado)).length,
    sinEvaluador: participantes.filter((item) => item.sin_evaluador).length,
  };
}

export function ordenarParticipantes(lista: ParticipanteApi[]): ParticipanteApi[] {
  return [...lista].sort((a, b) => {
    const apellido = (a.evaluado?.last_name ?? '').localeCompare(b.evaluado?.last_name ?? '', 'es');
    if (apellido) {
      return apellido;
    }
    const nombre = (a.evaluado?.first_name ?? '').localeCompare(b.evaluado?.first_name ?? '', 'es');
    if (nombre) {
      return nombre;
    }
    return a.id - b.id;
  });
}

export function listarTodo<T>(http: HttpClient, url: string): Observable<T[]> {
  const separador = url.includes('?') ? '&' : '?';
  return http.get<Pagina<T>>(`${url}${separador}page_size=100`).pipe(
    expand((pagina) => (pagina.next ? http.get<Pagina<T>>(pagina.next) : EMPTY)),
    reduce((acc, pagina) => acc.concat(pagina.results), [] as T[]),
  );
}

function textosError(valor: unknown): string[] {
  if (valor == null || valor === '') {
    return [];
  }
  if (typeof valor === 'string') {
    return [valor];
  }
  if (typeof valor === 'number' || typeof valor === 'boolean') {
    return [String(valor)];
  }
  if (Array.isArray(valor)) {
    return valor.flatMap((item) => textosError(item));
  }
  if (typeof valor === 'object') {
    const obj = valor as Record<string, unknown>;
    if (typeof obj['message'] === 'string') {
      return [obj['message']];
    }
    return Object.values(obj).flatMap((item) => textosError(item));
  }
  return [];
}

function filaError(valor: unknown): { generales: string[]; campos: Record<string, string[]> } {
  const campos: Record<string, string[]> = {};
  const generales: string[] = [];
  if (!valor || typeof valor !== 'object' || Array.isArray(valor)) {
    generales.push(...textosError(valor));
    return { generales, campos };
  }
  for (const [clave, item] of Object.entries(valor as Record<string, unknown>)) {
    if (clave === 'non_field_errors') {
      generales.push(...textosError(item));
    } else {
      campos[clave] = textosError(item);
    }
  }
  return { generales, campos };
}

export function parsearErrores(error: unknown): ErroresApi {
  const resultado = erroresVacios();
  const data = (error as { error?: unknown })?.error;
  if (!data) {
    resultado.generales.push('No se pudo completar la operación.');
    return resultado;
  }
  if (typeof data === 'string') {
    resultado.generales.push(data);
    return resultado;
  }
  if (typeof data !== 'object') {
    return resultado;
  }
  for (const [clave, valor] of Object.entries(data as Record<string, unknown>)) {
    if (clave === 'detail' || clave === 'non_field_errors') {
      resultado.generales.push(...textosError(valor));
      continue;
    }
    if (clave === 'criterios') {
      if (typeof valor === 'string' || (Array.isArray(valor) && valor.every((item) => typeof item === 'string'))) {
        resultado.criteriosGenerales.push(...textosError(valor));
        continue;
      }
      if (Array.isArray(valor)) {
        valor.forEach((fila, index) => {
          resultado.filas[index] = filaError(fila);
        });
        continue;
      }
      if (valor && typeof valor === 'object') {
        const entradas = Object.entries(valor as Record<string, unknown>);
        if (entradas.length && entradas.every(([key]) => /^\d+$/.test(key))) {
          for (const [key, fila] of entradas) {
            resultado.filas[Number(key)] = filaError(fila);
          }
          continue;
        }
      }
      resultado.criteriosGenerales.push(...textosError(valor));
      continue;
    }
    resultado.campos[clave] = textosError(valor);
  }
  return resultado;
}
