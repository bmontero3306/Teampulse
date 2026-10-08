export function mensajeError(error: unknown): string {
  const data = (error as { error?: unknown })?.error as
    | { detail?: unknown; [key: string]: unknown }
    | string
    | undefined;
  if (!data) {
    return 'No se pudo completar la operación.';
  }
  if (typeof data === 'string') {
    return data;
  }
  const detail = data.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    const texto = (detail as { detail?: string }).detail;
    if (texto) {
      return texto;
    }
  }
  const partes: string[] = [];
  for (const [clave, valor] of Object.entries(data)) {
    if (clave === 'detail') {
      continue;
    }
    if (Array.isArray(valor)) {
      partes.push(valor.join(' '));
    } else if (typeof valor === 'string') {
      partes.push(valor);
    }
  }
  return partes.join(' ') || 'Revisá los datos ingresados.';
}
