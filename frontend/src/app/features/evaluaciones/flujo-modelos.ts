import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, catchError, expand, forkJoin, map, of, reduce } from 'rxjs';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';

export interface UsuarioBreve {
  id: number;
  email: string;
  nombre: string;
}

export interface RespuestaFlujo {
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

export interface EvaluacionLista {
  id: number;
  ciclo: number;
  ciclo_nombre: string;
  estado: string;
  estado_display: string;
  en_borrador?: boolean;
  con_observacion?: boolean;
  evaluado?: UsuarioBreve | null;
  evaluador?: UsuarioBreve | null;
  puesto_nombre: string;
  sin_evaluador: boolean;
  comparacion_revelada: boolean;
  esta_cerrada?: boolean;
}

export interface EvaluacionDetalle extends EvaluacionLista {
  feedback_supervisor?: string;
  reunion_fecha?: string | null;
  reunion_notas?: string;
  comentario_empleado_cierre?: string;
  firmada_en?: string | null;
  firma_hash?: string;
  respuestas?: RespuestaFlujo[];
}

export interface CicloFlujo {
  id: number;
  fecha_cierre: string;
  criterios_generales?: string;
  nombre?: string;
}

export interface GrupoItems<T> {
  nombre: string | null;
  items: T[];
}

interface CompetenciaBreve {
  id: number;
  nombre: string;
  descripcion: string;
}

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

const ZONA = 'America/Argentina/Buenos_Aires';

export function puedeLeerCiclos(rol: string | undefined): boolean {
  return rol === 'supervisor' || rol === 'admin_rrhh' || rol === 'superadmin';
}

export function nombrePersona(usuario: UsuarioBreve | null | undefined): string {
  if (!usuario) {
    return '—';
  }
  return usuario.nombre || usuario.email || '—';
}

export function fechaLarga(iso: string | null | undefined): string {
  if (!iso) {
    return '—';
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) {
    return iso;
  }
  const mes = MESES[Number(match[2]) - 1];
  if (!mes) {
    return iso;
  }
  return `${Number(match[3])} de ${mes} de ${match[1]}`;
}

export function fechaHoraLarga(iso: string | null | undefined): string {
  if (!iso) {
    return '';
  }
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) {
    return iso;
  }
  const partes = new Intl.DateTimeFormat('en-US', {
    timeZone: ZONA,
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(fecha);
  const valor = (tipo: Intl.DateTimeFormatPartTypes) => partes.find((parte) => parte.type === tipo)?.value ?? '';
  const mes = MESES[Number(valor('month')) - 1];
  if (!mes) {
    return iso;
  }
  return `${Number(valor('day'))} de ${mes} de ${valor('year')} a las ${valor('hour')}:${valor('minute')}`;
}

export function brechaDisplay(brecha: number | null, esTexto: boolean): string {
  if (esTexto || brecha == null) {
    return '—';
  }
  if (brecha > 0) {
    return `+${brecha}`;
  }
  return String(brecha);
}

export function agruparItems<T extends { categoria: string }>(objetos: T[]): GrupoItems<T>[] {
  const grupos: GrupoItems<T>[] = [];
  const indice = new Map<string, number>();
  let hayCon = false;
  let haySin = false;
  for (const obj of objetos) {
    const nombre = (obj.categoria || '').trim();
    if (nombre) {
      hayCon = true;
    } else {
      haySin = true;
    }
    if (!indice.has(nombre)) {
      indice.set(nombre, grupos.length);
      grupos.push({ nombre: nombre || null, items: [] });
    }
    grupos[indice.get(nombre)!].items.push(obj);
  }
  if (hayCon && haySin) {
    for (const grupo of grupos) {
      if (!grupo.nombre) {
        grupo.nombre = 'Sin categoría';
      }
    }
  }
  return grupos;
}

export function escalaDe(item: RespuestaFlujo): number[] {
  const valores: number[] = [];
  if (item.escala_min == null || item.escala_max == null || item.escala_min > item.escala_max) {
    return valores;
  }
  for (let n = item.escala_min; n <= item.escala_max; n += 1) {
    valores.push(n);
  }
  return valores;
}

export function esTexto(item: RespuestaFlujo): boolean {
  return item.tipo_item === 'texto';
}

function listarTodas<T>(http: HttpClient, url: string): Observable<T[]> {
  return http.get<Pagina<T> | T[]>(url).pipe(
    expand((resp) => {
      if (Array.isArray(resp) || !resp.next) {
        return EMPTY;
      }
      return http.get<Pagina<T>>(resp.next);
    }),
    map((resp) => (Array.isArray(resp) ? resp : resp.results)),
    reduce((acc, pagina) => acc.concat(pagina), [] as T[]),
  );
}

export function cargarDescripciones(http: HttpClient): Observable<Record<string, string>> {
  return listarTodas<CompetenciaBreve>(http, `${API}/competencias/?page_size=100`).pipe(
    map((lista) => {
      const mapa: Record<string, string> = {};
      for (const item of lista) {
        const texto = (item.descripcion || '').trim();
        if (texto && !mapa[item.nombre]) {
          mapa[item.nombre] = texto;
        }
      }
      return mapa;
    }),
    catchError(() => of({})),
  );
}

export function cargarCiclosVisibles(
  http: HttpClient,
  ids: number[],
  rol: string | undefined,
): Observable<Record<number, CicloFlujo>> {
  const unicos = [...new Set(ids)];
  if (!unicos.length) {
    return of({});
  }
  if (puedeLeerCiclos(rol)) {
    return forkJoin(
      unicos.map((id) => http.get<CicloFlujo>(`${API}/ciclos/${id}/`).pipe(catchError(() => of(null)))),
    ).pipe(
      map((ciclos) => {
        const mapa: Record<number, CicloFlujo> = {};
        for (const ciclo of ciclos) {
          if (ciclo) {
            mapa[ciclo.id] = ciclo;
          }
        }
        return mapa;
      }),
    );
  }
  return http.get<{ ciclo_activo: CicloFlujo | null }>(`${API}/dashboard/`).pipe(
    map((dash) => {
      const ciclo = dash.ciclo_activo;
      if (!ciclo || !unicos.includes(ciclo.id)) {
        return {};
      }
      return { [ciclo.id]: ciclo };
    }),
    catchError(() => of({})),
  );
}
