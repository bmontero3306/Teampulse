import { Injectable, signal } from '@angular/core';

import { EMPRESA_KEY } from './api';

@Injectable({ providedIn: 'root' })
export class TenantService {
  readonly empresaId = signal<number | null>(this.leer());

  setEmpresa(id: number | null): void {
    if (id == null) {
      localStorage.removeItem(EMPRESA_KEY);
      this.empresaId.set(null);
      return;
    }
    localStorage.setItem(EMPRESA_KEY, String(id));
    this.empresaId.set(id);
  }

  private leer(): number | null {
    const raw = localStorage.getItem(EMPRESA_KEY);
    if (!raw) {
      return null;
    }
    const id = Number(raw);
    return Number.isFinite(id) ? id : null;
  }
}
