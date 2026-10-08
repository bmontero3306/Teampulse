import { Injectable, signal } from '@angular/core';

export interface Alerta {
  id: number;
  tipo: 'success' | 'error';
  texto: string;
}

@Injectable({ providedIn: 'root' })
export class AlertService {
  private seq = 0;
  readonly alertas = signal<Alerta[]>([]);

  success(texto: string): void {
    this.publicar('success', texto);
  }

  error(texto: string): void {
    this.publicar('error', texto);
  }

  cerrar(id: number): void {
    this.alertas.update((lista) => lista.filter((item) => item.id !== id));
  }

  private publicar(tipo: Alerta['tipo'], texto: string): void {
    const id = ++this.seq;
    this.alertas.update((lista) => [...lista, { id, tipo, texto }]);
    setTimeout(() => this.cerrar(id), 5000);
  }
}
