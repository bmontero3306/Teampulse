export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  first_name: string;
  last_name: string;
  rol: string;
  rol_display: string;
  empresa: number | null;
  empresa_nombre?: string | null;
  dni?: string;
  puesto?: number | null;
  puesto_nombre?: string | null;
  area?: number | null;
  area_nombre?: string | null;
  supervisor?: number | null;
  supervisor_nombre?: string | null;
  is_active?: boolean;
  bloqueado?: boolean;
  must_change_password: boolean;
}

export interface NavItem {
  clave: string;
  etiqueta: string;
  icono: string;
  href: string;
}

export interface EmpresaActual {
  id: number;
  nombre: string;
  estado: string;
}

export interface Sesion {
  token?: string;
  usuario: Usuario;
  empresa_actual: EmpresaActual | null;
  nav: NavItem[];
  notificaciones_no_leidas: number;
  debe_cambiar_clave: boolean;
}

export interface Pagina<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Columna {
  field: string;
  header: string;
}
