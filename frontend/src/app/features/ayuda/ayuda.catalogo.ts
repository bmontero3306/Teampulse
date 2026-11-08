/** Catálogo de Ayuda, alineado con app/ayuda.py (slugs, títulos y visibilidad por rol). */

export interface PaginaAyuda {
  slug: string;
  titulo: string;
  resumen: string;
  icono: string;
  grupo: string;
  roles: readonly string[] | null;
}

export interface GrupoAyuda {
  nombre: string;
  paginas: PaginaAyuda[];
}

const ROLES_GESTION = ['admin_rrhh', 'supervisor', 'superadmin'] as const;
const ROLES_RRHH = ['admin_rrhh', 'superadmin'] as const;
const ROLES_SUPERADMIN = ['superadmin'] as const;

export const PAGINAS_AYUDA: readonly PaginaAyuda[] = [
  {
    slug: 'inicio',
    titulo: 'Cómo funciona TeamPulse',
    resumen: 'Qué es el sistema, qué piezas hay y en qué orden se usa.',
    icono: 'book-open',
    grupo: 'Empezar',
    roles: null,
  },
  {
    slug: 'roles',
    titulo: 'Roles y permisos',
    resumen: 'Qué puede hacer cada rol y qué ve en el menú.',
    icono: 'shield',
    grupo: 'Empezar',
    roles: null,
  },
  {
    slug: 'organizacion',
    titulo: 'Organización',
    resumen: 'Empresas, áreas, puestos, organigrama y competencias.',
    icono: 'network',
    grupo: 'Configuración',
    roles: ROLES_GESTION,
  },
  {
    slug: 'plantillas',
    titulo: 'Plantillas de evaluación',
    resumen: 'Criterios, escalas, ponderaciones y asignación a puestos.',
    icono: 'clipboard-list',
    grupo: 'Configuración',
    roles: ROLES_GESTION,
  },
  {
    slug: 'ciclos',
    titulo: 'Ciclos de evaluación',
    resumen: 'Estados del ciclo, activación, pausa, cierre y participantes.',
    icono: 'calendar',
    grupo: 'Configuración',
    roles: ROLES_GESTION,
  },
  {
    slug: 'flujo',
    titulo: 'Flujo de una evaluación',
    resumen: 'Estados, quién actúa en cada paso y qué pasa después.',
    icono: 'git-branch',
    grupo: 'Evaluación',
    roles: null,
  },
  {
    slug: 'conformidad',
    titulo: 'Firma y conformidad',
    resumen: 'Reunión de feedback, firma, observación y comprobante.',
    icono: 'pen-line',
    grupo: 'Evaluación',
    roles: null,
  },
  {
    slug: 'notificaciones',
    titulo: 'Notificaciones',
    resumen: 'Avisos in-app, email y recordatorios de vencimiento.',
    icono: 'bell',
    grupo: 'Seguimiento',
    roles: null,
  },
  {
    slug: 'reportes',
    titulo: 'Reportes',
    resumen: 'Filtros, exportación PDF/Excel y trazabilidad de la exportación.',
    icono: 'chart-column',
    grupo: 'Seguimiento',
    roles: ROLES_RRHH,
  },
  {
    slug: 'auditoria',
    titulo: 'Auditoría',
    resumen: 'Qué se registra, quién puede verlo y qué datos se ocultan.',
    icono: 'shield-check',
    grupo: 'Seguimiento',
    roles: ROLES_RRHH,
  },
  {
    slug: 'empresas',
    titulo: 'Empresas y plataforma',
    resumen: 'Tenants, estados de empresa y selector de contexto.',
    icono: 'building-2',
    grupo: 'Plataforma',
    roles: ROLES_SUPERADMIN,
  },
];

export function paginasVisibles(rol: string | null | undefined): PaginaAyuda[] {
  return PAGINAS_AYUDA.filter(
    (pagina) => pagina.roles === null || (rol != null && pagina.roles.includes(rol)),
  );
}

export function paginaPorSlug(slug: string): PaginaAyuda | null {
  return PAGINAS_AYUDA.find((pagina) => pagina.slug === slug) ?? null;
}

export function gruposAyuda(rol: string | null | undefined): GrupoAyuda[] {
  const grupos: GrupoAyuda[] = [];
  const vistos = new Map<string, number>();
  for (const pagina of paginasVisibles(rol)) {
    const indice = vistos.get(pagina.grupo);
    if (indice === undefined) {
      vistos.set(pagina.grupo, grupos.length);
      grupos.push({ nombre: pagina.grupo, paginas: [pagina] });
    } else {
      grupos[indice].paginas.push(pagina);
    }
  }
  return grupos;
}
