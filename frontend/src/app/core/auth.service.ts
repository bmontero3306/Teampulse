import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, finalize, of, tap } from 'rxjs';

import { API, TOKEN_KEY } from './api';
import { Sesion } from './models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly session = signal<Sesion | null>(null);
  readonly sesion = this.session.asReadonly();

  token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  login(email: string, password: string): Observable<Sesion> {
    return this.http
      .post<Sesion>(`${API}/auth/login/`, { email, password })
      .pipe(tap((data) => this.guardar(data)));
  }

  loadMe(): Observable<Sesion | null> {
    if (!this.token()) {
      this.session.set(null);
      return of(null);
    }
    return this.http.get<Sesion>(`${API}/auth/me/`).pipe(
      tap((data) => this.session.set(data)),
      catchError(() => {
        this.clear();
        return of(null);
      }),
    );
  }

  cambiarClave(oldPassword: string, newPassword: string): Observable<Sesion> {
    return this.http
      .post<Sesion>(`${API}/auth/password/change/`, {
        old_password: oldPassword,
        new_password: newPassword,
      })
      .pipe(tap((data) => this.guardar(data)));
  }

  solicitarReset(email: string): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API}/auth/password/reset/`, { email });
  }

  confirmarReset(uid: string, token: string, newPassword: string): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API}/auth/password/reset/confirm/`, {
      uid,
      token,
      new_password: newPassword,
    });
  }

  logout(): Observable<unknown> {
    return this.http.post(`${API}/auth/logout/`, {}).pipe(finalize(() => this.clear()));
  }

  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.session.set(null);
  }

  private guardar(data: Sesion): void {
    if (data.token) {
      localStorage.setItem(TOKEN_KEY, data.token);
    }
    this.session.set(data);
  }
}
