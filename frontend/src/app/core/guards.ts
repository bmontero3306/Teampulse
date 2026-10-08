import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';

import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.token()) {
    return router.createUrlTree(['/login']);
  }
  if (auth.sesion()) {
    return true;
  }
  return auth.loadMe().pipe(map((sesion) => (sesion ? true : router.createUrlTree(['/login']))));
};

export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.token()) {
    return true;
  }
  return router.createUrlTree(['/dashboard']);
};

export const mustChangePasswordGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const sesion = auth.sesion();
  if (sesion) {
    return sesion.debe_cambiar_clave || sesion.usuario.must_change_password
      ? router.createUrlTree(['/clave'])
      : true;
  }
  return auth.loadMe().pipe(
    map((cargada) => {
      if (!cargada) {
        return router.createUrlTree(['/login']);
      }
      return cargada.debe_cambiar_clave || cargada.usuario.must_change_password
        ? router.createUrlTree(['/clave'])
        : true;
    }),
  );
};

export const claveGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.token()) {
    return router.createUrlTree(['/login']);
  }
  const listo = (debe: boolean) => (debe ? true : router.createUrlTree(['/dashboard']));
  const sesion = auth.sesion();
  if (sesion) {
    return listo(sesion.debe_cambiar_clave || sesion.usuario.must_change_password);
  }
  return auth.loadMe().pipe(
    map((cargada) =>
      cargada
        ? listo(cargada.debe_cambiar_clave || cargada.usuario.must_change_password)
        : router.createUrlTree(['/login']),
    ),
  );
};

export const rolGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const roles = (route.data['roles'] as string[] | undefined) ?? [];
  const permitir = (rol: string | undefined) =>
    !roles.length || (rol != null && roles.includes(rol)) ? true : router.createUrlTree(['/dashboard']);
  const sesion = auth.sesion();
  if (sesion) {
    return permitir(sesion.usuario.rol);
  }
  return auth.loadMe().pipe(map((cargada) => (cargada ? permitir(cargada.usuario.rol) : router.createUrlTree(['/login']))));
};
