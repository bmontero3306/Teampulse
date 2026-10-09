export interface Empresa {
  id: number;
  nombre: string;
  razon_social: string;
  cuit: string;
  email_contacto: string;
  telefono: string;
  direccion: string;
  estado: string;
  cantidad_usuarios?: number | null;
}

export interface EmpresaPayload {
  nombre: string;
  razon_social: string;
  cuit: string;
  email_contacto: string;
  telefono: string;
  direccion: string;
  estado: string;
}

export interface ErroresEmpresa {
  generales: string[];
  campos: Record<string, string[]>;
}

export const ERRORES_VACIOS: ErroresEmpresa = { generales: [], campos: {} };

export const ESTADOS_EMPRESA: { value: string; label: string }[] = [
  { value: 'activa', label: 'Activa' },
  { value: 'suspendida', label: 'Suspendida' },
  { value: 'inactiva', label: 'Inactiva' },
];

export type VistaEmpresa = 'lista' | 'nueva' | 'editar' | 'detalle' | 'suspender';

export function esVistaEmpresa(valor: string | null): valor is Exclude<VistaEmpresa, 'lista'> {
  return valor === 'nueva' || valor === 'editar' || valor === 'detalle' || valor === 'suspender';
}

export function formatearCuit(cuit: string | null | undefined): string {
  const digitos = (cuit ?? '').replace(/\D/g, '');
  if (digitos.length !== 11) {
    return cuit ?? '';
  }
  return `${digitos.slice(0, 2)}-${digitos.slice(2, 10)}-${digitos.slice(10)}`;
}

export function erroresEmpresa(error: unknown): ErroresEmpresa {
  const data = (error as { error?: unknown })?.error;
  const resultado: ErroresEmpresa = { generales: [], campos: {} };
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    resultado.generales = ['No se pudo completar la operación.'];
    return resultado;
  }
  for (const [clave, valor] of Object.entries(data as Record<string, unknown>)) {
    const textos = aTextos(valor);
    if (!textos.length) {
      continue;
    }
    if (clave === 'non_field_errors' || clave === '__all__' || clave === 'detail') {
      resultado.generales.push(...textos);
    } else {
      resultado.campos[clave] = textos;
    }
  }
  if (!resultado.generales.length && !Object.keys(resultado.campos).length) {
    resultado.generales = ['Revisá los datos ingresados.'];
  }
  return resultado;
}

function aTextos(valor: unknown): string[] {
  if (typeof valor === 'string') {
    return [valor];
  }
  if (Array.isArray(valor)) {
    return valor.flatMap((item) => aTextos(item));
  }
  return [];
}
