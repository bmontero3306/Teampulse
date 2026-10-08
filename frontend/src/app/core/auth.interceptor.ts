import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { EMPRESA_KEY, TOKEN_KEY } from './api';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  let headers = req.headers;
  const token = localStorage.getItem(TOKEN_KEY);
  const empresa = localStorage.getItem(EMPRESA_KEY);
  if (token) {
    headers = headers.set('Authorization', `Token ${token}`);
  }
  if (empresa) {
    headers = headers.set('X-Empresa-Id', empresa);
  }
  return next(req.clone({ headers }));
};

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  return next(req).pipe(
    catchError((error) => {
      const code = error?.error?.detail?.code;
      if (error.status === 401 && !req.url.includes('/auth/login')) {
        localStorage.removeItem(TOKEN_KEY);
        router.navigate(['/login']);
      } else if (error.status === 403 && code === 'must_change_password') {
        router.navigate(['/clave']);
      }
      return throwError(() => error);
    }),
  );
};
