"""Servicios de reportes ISO 9001 (CU06 / WP7)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.formats import date_format

from app.querysets import for_empresa
from evaluaciones.models import Evaluacion

ESTADOS_AUTO_COMPLETA = frozenset(
    {
        Evaluacion.Estado.SUPERVISOR,
        Evaluacion.Estado.PENDIENTE_REUNION,
        Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
        Evaluacion.Estado.CERRADA,
    }
)
ESTADOS_SUPERVISOR = frozenset(
    {
        Evaluacion.Estado.PENDIENTE_REUNION,
        Evaluacion.Estado.PENDIENTE_CONFORMIDAD,
        Evaluacion.Estado.CERRADA,
    }
)
ESTADOS_FIRMADAS = frozenset({Evaluacion.Estado.CERRADA})
CONFORMIDAD_CON_OBSERVACION = "con_observacion"

CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_EXCEL = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

CONFORMIDAD_NO_FIRMADA = "no_firmada"


@dataclass
class IsoIndicadores:
    total: int
    auto_completas: int
    pct_auto: float
    supervisor: int
    pct_supervisor: float
    firmadas: int
    pct_firmadas: float
    con_observacion: int
    pct_observacion: float
    promedio_auto: timedelta | None
    promedio_supervisor: timedelta | None
    promedio_firma: timedelta | None

    @property
    def promedio_auto_txt(self) -> str:
        return _fmt_duracion(self.promedio_auto)

    @property
    def promedio_supervisor_txt(self) -> str:
        return _fmt_duracion(self.promedio_supervisor)

    @property
    def promedio_firma_txt(self) -> str:
        return _fmt_duracion(self.promedio_firma)


@dataclass
class IsoReporte:
    queryset: QuerySet
    indicadores: IsoIndicadores
    empresa: object | None
    periodo_desde: date | None
    periodo_hasta: date | None
    filtros: dict


def generar_iso_queryset(filtros: dict) -> QuerySet:
    """Dataset común para preview HTML, PDF y Excel. Siempre acotado por empresa."""
    empresa = filtros.get("empresa")
    qs = Evaluacion.objects.select_related(
        "ciclo",
        "empresa",
        "evaluado",
        "evaluado__area",
        "evaluador",
        "puesto",
        "puesto__area",
        "plantilla",
    ).prefetch_related("respuestas").order_by(
        "ciclo__fecha_inicio", "evaluado__last_name", "evaluado__email", "pk"
    )
    qs = for_empresa(qs, empresa)

    ciclo = filtros.get("ciclo")
    if ciclo is not None:
        if getattr(ciclo, "empresa_id", None) and empresa and ciclo.empresa_id != empresa.pk:
            return qs.none()
        qs = qs.filter(ciclo=ciclo)

    area = filtros.get("area")
    if area is not None:
        if getattr(area, "empresa_id", None) and empresa and area.empresa_id != empresa.pk:
            return qs.none()
        qs = qs.filter(Q(evaluado__area=area) | Q(puesto__area=area))

    estado = filtros.get("estado") or filtros.get("estado_conformidad")
    if estado:
        if estado == CONFORMIDAD_NO_FIRMADA:
            qs = qs.exclude(estado__in=ESTADOS_FIRMADAS)
        elif estado == CONFORMIDAD_CON_OBSERVACION:
            qs = qs.filter(estado=Evaluacion.Estado.CERRADA).exclude(
                comentario_empleado_cierre=""
            )
        elif estado == Evaluacion.Estado.CERRADA:
            qs = qs.filter(
                estado=Evaluacion.Estado.CERRADA,
                comentario_empleado_cierre="",
            )
        else:
            qs = qs.filter(estado=estado)

    fecha_desde = filtros.get("fecha_desde")
    fecha_hasta = filtros.get("fecha_hasta")
    if fecha_desde:
        qs = qs.filter(ciclo__fecha_cierre__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(ciclo__fecha_inicio__lte=fecha_hasta)

    return qs


def calcular_indicadores_iso(queryset: QuerySet) -> IsoIndicadores:
    evaluaciones = list(queryset)
    total = len(evaluaciones)
    auto_completas = sum(1 for ev in evaluaciones if ev.estado in ESTADOS_AUTO_COMPLETA)
    supervisor = sum(1 for ev in evaluaciones if ev.estado in ESTADOS_SUPERVISOR)
    firmadas = sum(1 for ev in evaluaciones if ev.estado in ESTADOS_FIRMADAS)
    con_obs = sum(1 for ev in evaluaciones if ev.con_observacion)
    return IsoIndicadores(
        total=total,
        auto_completas=auto_completas,
        pct_auto=_porcentaje(auto_completas, total),
        supervisor=supervisor,
        pct_supervisor=_porcentaje(supervisor, total),
        firmadas=firmadas,
        pct_firmadas=_porcentaje(firmadas, total),
        con_observacion=con_obs,
        pct_observacion=_porcentaje(con_obs, total),
        promedio_auto=_promedio_duraciones(
            [
                (ev.ciclo.activado_en, ev.enviada_auto_en)
                for ev in evaluaciones
            ]
        ),
        promedio_supervisor=_promedio_duraciones(
            [
                (ev.enviada_auto_en, ev.cerrada_supervisor_en)
                for ev in evaluaciones
            ]
        ),
        promedio_firma=_promedio_duraciones(
            [
                (ev.cerrada_supervisor_en, ev.firmada_en)
                for ev in evaluaciones
            ]
        ),
    )


def construir_iso_reporte(filtros: dict) -> IsoReporte:
    queryset = generar_iso_queryset(filtros)
    periodo_desde, periodo_hasta = _resolver_periodo(filtros, queryset)
    return IsoReporte(
        queryset=queryset,
        indicadores=calcular_indicadores_iso(queryset),
        empresa=filtros.get("empresa"),
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        filtros=filtros,
    )


def exportar_iso_excel(reporte: IsoReporte, usuario=None, generado_en=None) -> bytes:
    """Libro Excel: hoja Resumen + hoja Detalle."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    generado_en = generado_en or timezone.localtime(timezone.now())
    wb = Workbook()

    ws_resumen = wb.active
    ws_resumen.title = "Resumen"
    encabezado = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="0EA5E9")
    label_font = Font(bold=True, color="0F172A")

    ws_resumen["A1"] = "Reporte ISO 9001 — Evaluaciones de desempeño"
    ws_resumen["A1"].font = Font(bold=True, size=14, color="0F172A")
    ws_resumen.merge_cells("A1:B1")

    filas_meta = [
        ("Empresa", _nombre_empresa(reporte.empresa)),
        ("Periodo", _texto_periodo(reporte.periodo_desde, reporte.periodo_hasta)),
        ("Generado", _texto_timestamp(generado_en)),
        ("Generado por", _nombre_usuario(usuario)),
    ]
    for i, (etiqueta, valor) in enumerate(filas_meta, start=3):
        ws_resumen[f"A{i}"] = etiqueta
        ws_resumen[f"A{i}"].font = label_font
        ws_resumen[f"B{i}"] = valor

    ind = reporte.indicadores
    ws_resumen["A8"] = "Indicador"
    ws_resumen["B8"] = "Valor"
    ws_resumen["A8"].font = encabezado
    ws_resumen["B8"].font = encabezado
    ws_resumen["A8"].fill = fill
    ws_resumen["B8"].fill = fill

    filas_ind = [
        ("Total de evaluaciones", ind.total),
        ("Autoevaluaciones completas", f"{ind.auto_completas} ({_fmt_pct(ind.pct_auto)})"),
        ("Evaluaciones de supervisor", f"{ind.supervisor} ({_fmt_pct(ind.pct_supervisor)})"),
        ("Firmadas", f"{ind.firmadas} ({_fmt_pct(ind.pct_firmadas)})"),
        ("Con observación", f"{ind.con_observacion} ({_fmt_pct(ind.pct_observacion)})"),
        ("Tiempo promedio — autoevaluación", _fmt_duracion(ind.promedio_auto)),
        ("Tiempo promedio — supervisor", _fmt_duracion(ind.promedio_supervisor)),
        ("Tiempo promedio — firma", _fmt_duracion(ind.promedio_firma)),
    ]
    for i, (etiqueta, valor) in enumerate(filas_ind, start=9):
        ws_resumen[f"A{i}"] = etiqueta
        ws_resumen[f"B{i}"] = valor

    ws_resumen.column_dimensions["A"].width = 42
    ws_resumen.column_dimensions["B"].width = 48

    ws_detalle = wb.create_sheet("Detalle")
    headers = [
        "Evaluado",
        "Evaluador",
        "Área",
        "Ciclo",
        "Estado",
        "Enviada autoevaluación",
        "Cerrada por supervisor",
        "Firmada",
        "Hash de firma",
        "Responsable de firma",
    ]
    for col, titulo in enumerate(headers, start=1):
        cell = ws_detalle.cell(row=1, column=col, value=titulo)
        cell.font = encabezado
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    for row_idx, ev in enumerate(reporte.queryset, start=2):
        valores = _fila_detalle(ev)
        for col, valor in enumerate(valores, start=1):
            ws_detalle.cell(row=row_idx, column=col, value=valor)

    anchos = [28, 28, 22, 24, 28, 22, 22, 22, 44, 28]
    for i, ancho in enumerate(anchos, start=1):
        ws_detalle.column_dimensions[get_column_letter(i)].width = ancho
    ws_detalle.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, reporte.indicadores.total + 1)}"
    ws_detalle.freeze_panes = "A2"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def exportar_iso_pdf(reporte: IsoReporte, usuario=None, generado_en=None) -> bytes:
    """PDF con encabezado de empresa, periodo, tabla y pie auditable."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    generado_en = generado_en or timezone.localtime(timezone.now())
    pie = (
        f"documento generado el {_texto_timestamp(generado_en)} "
        f"por {_nombre_usuario(usuario)}"
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Reporte ISO 9001",
        author=_nombre_usuario(usuario),
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "IsoTitulo",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    estilo_meta = ParagraphStyle(
        "IsoMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#334155"),
        leading=12,
    )
    estilo_celda = ParagraphStyle(
        "IsoCelda",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
    )
    estilo_th = ParagraphStyle(
        "IsoTh",
        parent=estilo_celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    estilo_kpi = ParagraphStyle(
        "IsoKpi",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
    )
    estilo_kpi_th = ParagraphStyle(
        "IsoKpiTh",
        parent=estilo_kpi,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = [
        Paragraph("Reporte ISO 9001 — Evaluaciones de desempeño", estilo_titulo),
        Paragraph(f"<b>Empresa:</b> {_escape(_nombre_empresa(reporte.empresa))}", estilo_meta),
        Paragraph(
            f"<b>Periodo:</b> {_escape(_texto_periodo(reporte.periodo_desde, reporte.periodo_hasta))}",
            estilo_meta,
        ),
        Spacer(1, 6 * mm),
    ]

    ind = reporte.indicadores
    kpis = [
        ["Total", "% Auto", "% Supervisor", "% Firmadas", "% Observación"],
        [
            str(ind.total),
            _fmt_pct(ind.pct_auto),
            _fmt_pct(ind.pct_supervisor),
            _fmt_pct(ind.pct_firmadas),
            _fmt_pct(ind.pct_observacion),
        ],
        [
            "",
            f"{ind.auto_completas} de {ind.total}",
            f"{ind.supervisor} de {ind.total}",
            f"{ind.firmadas} de {ind.total}",
            f"{ind.con_observacion} de {ind.total}",
        ],
    ]
    kpi_para = [
        [Paragraph(_escape(c), estilo_kpi_th if i == 0 else estilo_kpi) for c in fila]
        for i, fila in enumerate(kpis)
    ]
    tabla_kpi = Table(kpi_para, colWidths=[50 * mm] * 5)
    tabla_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tabla_kpi)
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Tiempos promedio — "
            f"autoevaluación: {_escape(_fmt_duracion(ind.promedio_auto))} · "
            f"supervisor: {_escape(_fmt_duracion(ind.promedio_supervisor))} · "
            f"firma: {_escape(_fmt_duracion(ind.promedio_firma))}",
            estilo_meta,
        )
    )
    story.append(Spacer(1, 5 * mm))

    headers = [
        "Evaluado",
        "Evaluador",
        "Estado",
        "Auto",
        "Supervisor",
        "Firma",
        "Hash",
    ]
    data = [[Paragraph(_escape(h), estilo_th) for h in headers]]
    for ev in reporte.queryset:
        fila = _fila_detalle(ev)
        celdas = [fila[0], fila[1], fila[4], fila[5], fila[6], fila[7], fila[8]]
        data.append([Paragraph(_escape(c), estilo_celda) for c in celdas])

    if len(data) == 1:
        data.append(
            [Paragraph("No hay evaluaciones para los filtros seleccionados.", estilo_celda)]
            + [Paragraph("", estilo_celda)] * 6
        )

    anchos = [45 * mm, 40 * mm, 38 * mm, 32 * mm, 32 * mm, 32 * mm, 54 * mm]
    tabla = Table(data, colWidths=anchos, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tabla)

    def _pie(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(12 * mm, 8 * mm, pie)
        canvas.drawRightString(
            landscape(A4)[0] - 12 * mm,
            8 * mm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()


def payload_auditoria_export(reporte: IsoReporte, formato: str) -> dict:
    filtros = reporte.filtros or {}
    return {
        "formato": formato,
        "total": reporte.indicadores.total,
        "ciclo_id": getattr(filtros.get("ciclo"), "pk", None),
        "area_id": getattr(filtros.get("area"), "pk", None),
        "estado": filtros.get("estado") or "",
        "fecha_desde": _iso_fecha(filtros.get("fecha_desde")),
        "fecha_hasta": _iso_fecha(filtros.get("fecha_hasta")),
        "empresa_id": getattr(reporte.empresa, "pk", None),
    }


def _porcentaje(parte: int, total: int) -> float:
    if not total:
        return 0.0
    return round(100.0 * parte / total, 1)


def _promedio_duraciones(pares) -> timedelta | None:
    segundos = []
    for inicio, fin in pares:
        if inicio is None or fin is None:
            continue
        delta = fin - inicio
        if delta.total_seconds() < 0:
            continue
        segundos.append(delta.total_seconds())
    if not segundos:
        return None
    return timedelta(seconds=sum(segundos) / len(segundos))


def _resolver_periodo(filtros: dict, queryset: QuerySet) -> tuple[date | None, date | None]:
    ciclo = filtros.get("ciclo")
    if ciclo is not None:
        return ciclo.fecha_inicio, ciclo.fecha_cierre
    desde = filtros.get("fecha_desde")
    hasta = filtros.get("fecha_hasta")
    if desde or hasta:
        return desde, hasta
    fechas = list(
        queryset.values_list("ciclo__fecha_inicio", "ciclo__fecha_cierre")[:500]
    )
    if not fechas:
        return None, None
    inicios = [f[0] for f in fechas if f[0]]
    cierres = [f[1] for f in fechas if f[1]]
    return (min(inicios) if inicios else None, max(cierres) if cierres else None)


def _fila_detalle(ev: Evaluacion) -> list[str]:
    area = ""
    if getattr(ev.evaluado, "area", None):
        area = ev.evaluado.area.nombre
    elif getattr(ev.puesto, "area", None):
        area = ev.puesto.area.nombre
    responsable_firma = ""
    if ev.firmada_en:
        responsable_firma = _nombre_usuario(ev.evaluado)
    return [
        _nombre_usuario(ev.evaluado),
        _nombre_usuario(ev.evaluador) if ev.evaluador_id else "—",
        area or "—",
        ev.ciclo.nombre if ev.ciclo_id else "—",
        ev.etiqueta_estado,
        _texto_dt(ev.enviada_auto_en),
        _texto_dt(ev.cerrada_supervisor_en),
        _texto_dt(ev.firmada_en),
        ev.firma_hash or "—",
        responsable_firma or "—",
    ]


def _nombre_usuario(usuario) -> str:
    if usuario is None:
        return "—"
    nombre = (usuario.get_full_name() or "").strip()
    return nombre or getattr(usuario, "email", None) or "—"


def _nombre_empresa(empresa) -> str:
    if empresa is None:
        return "—"
    return empresa.nombre


def _texto_periodo(desde, hasta) -> str:
    if desde and hasta:
        return f"{_texto_fecha(desde)} – {_texto_fecha(hasta)}"
    if desde:
        return f"Desde {_texto_fecha(desde)}"
    if hasta:
        return f"Hasta {_texto_fecha(hasta)}"
    return "Todos los periodos"


def _texto_fecha(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        return date_format(valor, "d/m/Y")
    return date_format(valor, "d/m/Y")


def _texto_dt(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        return date_format(valor, "d/m/Y H:i")
    return date_format(valor, "d/m/Y")


def _texto_timestamp(valor) -> str:
    if valor is None:
        valor = timezone.localtime(timezone.now())
    elif isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return date_format(valor, "d/m/Y H:i")


def _fmt_pct(valor: float) -> str:
    texto = f"{valor:.1f}".replace(".", ",")
    return f"{texto} %"


def _fmt_duracion(delta: timedelta | None) -> str:
    if delta is None:
        return "—"
    total_horas = delta.total_seconds() / 3600
    if total_horas < 24:
        texto = f"{total_horas:.1f}".replace(".", ",")
        return f"{texto} h"
    dias = total_horas / 24
    texto = f"{dias:.1f}".replace(".", ",")
    return f"{texto} días"


def _iso_fecha(valor):
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def _escape(texto) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
