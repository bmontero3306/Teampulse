import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { EMPTY, Observable, expand, reduce } from 'rxjs';

import { API } from '../../core/api';
import { Pagina } from '../../core/models';
import { Empresa, EmpresaPayload } from './empresa.model';

@Injectable({ providedIn: 'root' })
export class EmpresaApi {
  private readonly http = inject(HttpClient);

  listar(estado = ''): Observable<Empresa[]> {
    const params: Record<string, string> = { page_size: '100' };
    if (estado) {
      params['estado'] = estado;
    }
    return this.http.get<Pagina<Empresa>>(`${API}/empresas/`, { params }).pipe(
      expand((pagina) => (pagina.next ? this.http.get<Pagina<Empresa>>(urlPagina(pagina.next)) : EMPTY)),
      reduce((acc, pagina) => acc.concat(pagina.results ?? []), [] as Empresa[]),
    );
  }

  obtener(id: number): Observable<Empresa> {
    return this.http.get<Empresa>(`${API}/empresas/${id}/`);
  }

  crear(body: Partial<EmpresaPayload>): Observable<Empresa> {
    return this.http.post<Empresa>(`${API}/empresas/`, body);
  }

  actualizar(id: number, body: Partial<EmpresaPayload>): Observable<Empresa> {
    return this.http.patch<Empresa>(`${API}/empresas/${id}/`, body);
  }

  suspender(id: number): Observable<Empresa> {
    return this.http.post<Empresa>(`${API}/empresas/${id}/suspender/`, {});
  }

  activar(id: number): Observable<Empresa> {
    return this.http.post<Empresa>(`${API}/empresas/${id}/activar/`, {});
  }
}

function urlPagina(next: string): string {
  const url = new URL(next, 'http://localhost');
  return `${url.pathname}${url.search}`;
}
