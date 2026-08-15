"""PDF de resultado de evaluación (formato documental tipo comprobante)."""

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.utils import timezone
from django.utils.formats import date_format

from empresas.validators import formatear_cuit
from evaluaciones.models import Evaluacion

CONTENT_TYPE_PDF = "application/pdf"

_COLOR_NAVY = "#0f172a"
_COLOR_TEAL = "#0e7490"
_COLOR_SKY = "#0284c7"
_COLOR_SLATE = "#334155"
_COLOR_MUTED = "#64748b"
_COLOR_LINE = "#cbd5e1"
_COLOR_ROW = "#f8fafc"
_COLOR_OK = "#065f46"
_COLOR_OK_BG = "#ecfdf5"
_COLOR_WARN = "#92400e"
_COLOR_WARN_BG = "#fffbeb"


def numero_documento(evaluacion: Evaluacion) -> str:
    empresa_id = getattr(evaluacion, "empresa_id", 0) or 0
    return f"EV-{empresa_id:05d}-{evaluacion.pk:08d}"


def nombre_archivo_pdf(evaluacion: Evaluacion) -> str:
    return f"evaluacion-{numero_documento(evaluacion)}.pdf"


def exportar_resultado_pdf(evaluacion: Evaluacion, usuario=None, generado_en=None) -> bytes:
    """Comprobante A4 con empresa, logo TeamPulse, criterios y firma digital."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    generado_en = generado_en or timezone.localtime(timezone.now())
    empresa = evaluacion.empresa
    nro = numero_documento(evaluacion)
    revelada = evaluacion.comparacion_revelada
    items = list(
        evaluacion.respuestas.select_related("criterio", "criterio__competencia").order_by(
            "criterio__orden", "pk"
        )
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Evaluación de desempeño {nro}",
        author="TeamPulse",
        subject=f"{nro} | {evaluacion.firma_hash or 'sin-firma'}",
        creator="TeamPulse",
    )

    styles = getSampleStyleSheet()
    estilo_marca = ParagraphStyle(
        "EvMarca",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.HexColor(_COLOR_SKY),
        leading=16,
        spaceAfter=0,
    )
    estilo_empresa = ParagraphStyle(
        "EvEmpresa",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor(_COLOR_NAVY),
        leading=13,
        spaceAfter=1,
    )
    estilo_meta = ParagraphStyle(
        "EvMeta",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor(_COLOR_SLATE),
        leading=11,
    )
    estilo_titulo_doc = ParagraphStyle(
        "EvTituloDoc",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor(_COLOR_NAVY),
        alignment=TA_RIGHT,
        leading=15,
        spaceAfter=4,
    )
    estilo_doc_dato = ParagraphStyle(
        "EvDocDato",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor(_COLOR_SLATE),
        alignment=TA_RIGHT,
        leading=11,
    )
    estilo_seccion = ParagraphStyle(
        "EvSeccion",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.white,
        leading=12,
    )
    estilo_label = ParagraphStyle(
        "EvLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        textColor=colors.HexColor(_COLOR_MUTED),
        leading=10,
    )
    estilo_valor = ParagraphStyle(
        "EvValor",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor(_COLOR_NAVY),
        leading=11,
    )
    estilo_th = ParagraphStyle(
        "EvTh",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        textColor=colors.white,
        leading=10,
    )
    estilo_th_center = ParagraphStyle(
        "EvThCenter",
        parent=estilo_th,
        alignment=TA_CENTER,
    )
    estilo_td = ParagraphStyle(
        "EvTd",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor(_COLOR_NAVY),
        leading=10,
    )
    estilo_td_center = ParagraphStyle(
        "EvTdCenter",
        parent=estilo_td,
        alignment=TA_CENTER,
    )
    estilo_cuerpo = ParagraphStyle(
        "EvCuerpo",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor(_COLOR_SLATE),
        leading=12,
    )
    estilo_legal = ParagraphStyle(
        "EvLegal",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor(_COLOR_MUTED),
        leading=9.5,
        alignment=TA_LEFT,
    )
    estilo_firma_titulo = ParagraphStyle(
        "EvFirmaTitulo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor(_COLOR_OK),
        alignment=TA_CENTER,
        leading=11,
    )
    estilo_firma_pendiente = ParagraphStyle(
        "EvFirmaPendiente",
        parent=estilo_firma_titulo,
        textColor=colors.HexColor(_COLOR_WARN),
    )
    estilo_firma_nombre = ParagraphStyle(
        "EvFirmaNombre",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor(_COLOR_NAVY),
        alignment=TA_CENTER,
        leading=14,
        spaceBefore=6,
        spaceAfter=2,
    )
    estilo_firma_cap = ParagraphStyle(
        "EvFirmaCap",
        parent=styles["Normal"],
        fontSize=6.5,
        textColor=colors.HexColor(_COLOR_MUTED),
        alignment=TA_CENTER,
        leading=9,
    )
    estilo_firma_dato = ParagraphStyle(
        "EvFirmaDato",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=colors.HexColor(_COLOR_SLATE),
        alignment=TA_CENTER,
        leading=10,
    )
    estilo_hash = ParagraphStyle(
        "EvHash",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.5,
        textColor=colors.HexColor(_COLOR_NAVY),
        alignment=TA_CENTER,
        leading=9,
    )
    estilo_kpi = ParagraphStyle(
        "EvKpi",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor(_COLOR_NAVY),
        alignment=TA_RIGHT,
        leading=14,
    )
    estilo_kpi_label = ParagraphStyle(
        "EvKpiLabel",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor(_COLOR_MUTED),
        alignment=TA_LEFT,
        leading=10,
    )

    def P(texto, estilo):
        return Paragraph(_escape(texto), estilo)

    story = []
    story.append(_tabla_encabezado(evaluacion, empresa, nro, styles_bundle={
        "marca": estilo_marca,
        "empresa": estilo_empresa,
        "meta": estilo_meta,
        "titulo": estilo_titulo_doc,
        "dato": estilo_doc_dato,
        "P": P,
    }))
    story.append(Spacer(1, 5 * mm))
    story.append(_banda("Datos de las partes", estilo_seccion))
    story.append(_tabla_partes(evaluacion, estilo_label, estilo_valor, P))
    story.append(Spacer(1, 3.5 * mm))
    story.append(_banda("Condiciones del ciclo", estilo_seccion))
    story.append(_tabla_condiciones(evaluacion, estilo_label, estilo_valor, P))
    story.append(Spacer(1, 4 * mm))
    story.append(_banda("Criterios evaluados", estilo_seccion))
    story.append(Spacer(1, 1.5 * mm))
    story.append(
        _tabla_criterios(
            items,
            revelada,
            estilo_th,
            estilo_th_center,
            estilo_td,
            estilo_td_center,
            P,
        )
    )

    comentarios = _tabla_comentarios(items, revelada, estilo_th, estilo_td, P)
    if comentarios is not None:
        story.append(Spacer(1, 4 * mm))
        story.append(_banda("Comentarios por criterio", estilo_seccion))
        story.append(Spacer(1, 1.5 * mm))
        story.append(comentarios)

    if revelada and (evaluacion.feedback_supervisor or "").strip():
        story.append(Spacer(1, 4 * mm))
        story.append(_banda("Feedback del supervisor", estilo_seccion))
        story.append(Spacer(1, 1.5 * mm))
        story.append(P(evaluacion.feedback_supervisor, estilo_cuerpo))

    if (evaluacion.reunion_notas or "").strip():
        story.append(Spacer(1, 4 * mm))
        story.append(_banda("Reunión de feedback", estilo_seccion))
        story.append(Spacer(1, 1.5 * mm))
        if evaluacion.reunion_fecha:
            story.append(
                Paragraph(
                    f"<b>Fecha:</b> {_escape(_texto_dt(evaluacion.reunion_fecha))}",
                    estilo_cuerpo,
                )
            )
        story.append(P(evaluacion.reunion_notas, estilo_cuerpo))

    story.append(Spacer(1, 4 * mm))
    story.append(
        _bloque_totales_y_firma(
            evaluacion,
            items,
            revelada,
            estilo_kpi_label,
            estilo_kpi,
            estilo_firma_titulo,
            estilo_firma_pendiente,
            estilo_firma_nombre,
            estilo_firma_cap,
            estilo_firma_dato,
            estilo_hash,
            estilo_legal,
            P,
        )
    )

    pie = (
        f"Documento generado el {_texto_timestamp(generado_en)} "
        f"por {_nombre_persona(usuario)} · TeamPulse"
    )

    class _Canvas(Canvas):
        def __init__(self, *args, **kwargs):
            kwargs["pageCompression"] = 0
            super().__init__(*args, **kwargs)

    def _pie(canvas, _doc):
        canvas.saveState()
        ancho, _alto = A4
        canvas.setStrokeColor(colors.HexColor(_COLOR_TEAL))
        canvas.setLineWidth(1.4)
        canvas.line(14 * mm, 12 * mm, ancho - 14 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor(_COLOR_MUTED))
        canvas.drawString(14 * mm, 7 * mm, pie)
        canvas.drawRightString(
            ancho - 14 * mm,
            7 * mm,
            f"{nro}  ·  Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie, canvasmaker=_Canvas)
    return buffer.getvalue()


def _tabla_encabezado(evaluacion, empresa, nro, styles_bundle):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    P = styles_bundle["P"]
    logo = _flowable_logo(22 * mm)
    lineas_empresa = _lineas_empresa(empresa)
    bloque_izq = []
    if logo is not None:
        marca = Table(
            [[logo, P("TeamPulse", styles_bundle["marca"])]],
            colWidths=[24 * mm, 82 * mm],
        )
        marca.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        bloque_izq.append(marca)
    else:
        bloque_izq.append(P("TeamPulse", styles_bundle["marca"]))
    bloque_izq.append(P(lineas_empresa[0], styles_bundle["empresa"]))
    for linea in lineas_empresa[1:]:
        bloque_izq.append(P(linea, styles_bundle["meta"]))

    titulo = (
        "COMPARACIÓN 180°"
        if evaluacion.comparacion_revelada
        else "EVALUACIÓN DE DESEMPEÑO"
    )
    fecha_doc = evaluacion.firmada_en or evaluacion.cerrada_supervisor_en or timezone.localtime(
        timezone.now()
    )
    bloque_der = [
        P(titulo, styles_bundle["titulo"]),
        Paragraph(
            f"<b>Nro.:</b> {_escape(nro)}",
            styles_bundle["dato"],
        ),
        Paragraph(
            f"<b>Fecha:</b> {_escape(_texto_fecha(fecha_doc))}",
            styles_bundle["dato"],
        ),
        Paragraph(
            f"<b>Estado:</b> {_escape(evaluacion.get_estado_display())}",
            styles_bundle["dato"],
        ),
    ]

    tabla = Table(
        [[bloque_izq, bloque_der]],
        colWidths=[112 * mm, 70 * mm],
    )
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LINEBEFORE", (1, 0), (1, 0), 1.2, colors.HexColor(_COLOR_TEAL)),
            ]
        )
    )
    return tabla


def _lineas_empresa(empresa) -> list[str]:
    if empresa is None:
        return ["TeamPulse"]
    lineas = [empresa.razon_social or empresa.nombre]
    cuit = formatear_cuit(empresa.cuit) if empresa.cuit else ""
    if cuit:
        lineas.append(f"C.U.I.T. {cuit}")
    if empresa.direccion:
        lineas.append(empresa.direccion)
    extras = []
    if empresa.telefono:
        extras.append(f"TEL: {empresa.telefono}")
    if empresa.email_contacto:
        extras.append(empresa.email_contacto)
    if extras:
        lineas.append(" · ".join(extras))
    if empresa.nombre and empresa.nombre != empresa.razon_social:
        lineas.insert(1, f"Nombre de fantasía: {empresa.nombre}")
    return lineas


def _tabla_partes(evaluacion, estilo_label, estilo_valor, P):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    evaluado = evaluacion.evaluado
    evaluador = evaluacion.evaluador
    puesto_eval = ""
    if getattr(evaluacion, "puesto", None):
        puesto_eval = evaluacion.puesto.nombre
    elif getattr(evaluado, "puesto", None):
        puesto_eval = evaluado.puesto.nombre

    izq = _mini_ficha(
        "Evaluado",
        [
            ("Nombre", _nombre_persona(evaluado)),
            ("DNI", getattr(evaluado, "dni", None) or "—"),
            ("Puesto", puesto_eval or "—"),
        ],
        estilo_label,
        estilo_valor,
        P,
    )
    der = _mini_ficha(
        "Evaluador",
        [
            ("Nombre", _nombre_persona(evaluador) if evaluador else "Sin evaluador"),
            ("DNI", (getattr(evaluador, "dni", None) or "—") if evaluador else "—"),
            (
                "Puesto",
                (
                    evaluador.puesto.nombre
                    if evaluador and getattr(evaluador, "puesto", None)
                    else "—"
                ),
            ),
        ],
        estilo_label,
        estilo_valor,
        P,
    )
    tabla = Table([[izq, der]], colWidths=[91 * mm, 91 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (0, 0), 2.5 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 2.5 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 2.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4 * mm),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_COLOR_ROW)),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(_COLOR_LINE)),
                ("LINEAFTER", (0, 0), (0, 0), 0.4, colors.HexColor(_COLOR_LINE)),
            ]
        )
    )
    return tabla


def _mini_ficha(titulo, pares, estilo_label, estilo_valor, P):
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    filas = [[Paragraph(f"<b>{_escape(titulo)}</b>", estilo_valor), ""]]
    for etiqueta, valor in pares:
        filas.append([P(etiqueta, estilo_label), P(valor or "—", estilo_valor)])
    tabla = Table(filas, colWidths=[16 * mm, 70 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
                ("TOPPADDING", (0, 0), (-1, 0), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0.8 * mm),
                ("TOPPADDING", (0, 1), (-1, -1), 0.4 * mm),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 0.4 * mm),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return tabla


def _tabla_condiciones(evaluacion, estilo_label, estilo_valor, P):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    ciclo = evaluacion.ciclo
    plantilla = evaluacion.plantilla
    periodo = "—"
    if ciclo and ciclo.fecha_inicio and ciclo.fecha_cierre:
        periodo = f"{_texto_fecha(ciclo.fecha_inicio)} – {_texto_fecha(ciclo.fecha_cierre)}"
    pares = [
        ("Ciclo", ciclo.nombre if ciclo else "—"),
        ("Periodo", periodo),
        ("Plantilla", plantilla.nombre if plantilla else "—"),
        ("Tipo", plantilla.get_tipo_display() if plantilla else "—"),
    ]
    celdas = []
    for etiqueta, valor in pares:
        celdas.append(
            Table(
                [[P(etiqueta, estilo_label)], [P(valor, estilo_valor)]],
                colWidths=[42 * mm],
            )
        )
    tabla = Table([celdas], colWidths=[45.5 * mm] * 4)
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(_COLOR_LINE)),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor(_COLOR_LINE)),
            ]
        )
    )
    return tabla


def _tabla_criterios(items, revelada, estilo_th, estilo_th_center, estilo_td, estilo_td_center, P):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    headers = [
        P("Criterio", estilo_th),
        P("Escala", estilo_th_center),
        P("Empleado", estilo_th_center),
        P("Supervisor", estilo_th_center),
        P("Brecha", estilo_th_center),
        P("Pond.", estilo_th_center),
    ]
    data = [headers]
    for item in items:
        criterio = item.criterio
        competencia = getattr(criterio, "competencia", None)
        nombre = competencia.nombre if competencia else "—"
        escala = f"{criterio.escala_min}–{criterio.escala_max}"
        pond = _fmt_decimal(criterio.ponderacion)
        emp = _fmt_entero(item.puntaje_empleado)
        if revelada:
            sup = _fmt_entero(item.puntaje_supervisor)
            brecha = item.brecha_display
        else:
            sup = "—"
            brecha = "—"
        data.append(
            [
                P(nombre, estilo_td),
                P(escala, estilo_td_center),
                P(emp, estilo_td_center),
                P(sup, estilo_td_center),
                P(brecha, estilo_td_center),
                P(pond, estilo_td_center),
            ]
        )
    if len(data) == 1:
        data.append(
            [P("Sin ítems de evaluación.", estilo_td)] + [P("", estilo_td)] * 5
        )

    anchos = [62 * mm, 22 * mm, 24 * mm, 26 * mm, 24 * mm, 24 * mm]
    tabla = Table(data, colWidths=anchos, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_COLOR_TEAL)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(_COLOR_ROW)]),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(_COLOR_LINE)),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return tabla


def _tabla_comentarios(items, revelada, estilo_th, estilo_td, P):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    filas_utiles = []
    for item in items:
        emp = (item.comentario_empleado or "").strip()
        sup = (item.comentario_supervisor or "").strip() if revelada else ""
        if not emp and not sup:
            continue
        filas_utiles.append(item)
    if not filas_utiles:
        return None

    data = [
        [
            P("Criterio", estilo_th),
            P("Comentario del empleado", estilo_th),
            P("Comentario del supervisor", estilo_th),
        ]
    ]
    for item in filas_utiles:
        competencia = getattr(item.criterio, "competencia", None)
        nombre = competencia.nombre if competencia else "—"
        emp = (item.comentario_empleado or "").strip() or "—"
        if revelada:
            sup = (item.comentario_supervisor or "").strip() or "—"
        else:
            sup = "—"
        data.append([P(nombre, estilo_td), P(emp, estilo_td), P(sup, estilo_td)])

    tabla = Table(data, colWidths=[42 * mm, 70 * mm, 70 * mm], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_COLOR_TEAL)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(_COLOR_ROW)]),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(_COLOR_LINE)),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    return tabla


def _bloque_totales_y_firma(
    evaluacion,
    items,
    revelada,
    estilo_kpi_label,
    estilo_kpi,
    estilo_firma_titulo,
    estilo_firma_pendiente,
    estilo_firma_nombre,
    estilo_firma_cap,
    estilo_firma_dato,
    estilo_hash,
    estilo_legal,
    P,
):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

    prom_emp = _promedio_ponderado(items, "puntaje_empleado")
    prom_sup = _promedio_ponderado(items, "puntaje_supervisor") if revelada else None
    filas_totales = [
        [P("Promedio ponderado — empleado", estilo_kpi_label), P(_fmt_promedio(prom_emp), estilo_kpi)],
    ]
    if revelada:
        filas_totales.append(
            [P("Promedio ponderado — supervisor", estilo_kpi_label), P(_fmt_promedio(prom_sup), estilo_kpi)]
        )
        brecha = None
        if prom_emp is not None and prom_sup is not None:
            brecha = prom_sup - prom_emp
        filas_totales.append(
            [P("Brecha promedio", estilo_kpi_label), P(_fmt_brecha_prom(brecha), estilo_kpi)]
        )
    totales = Table(filas_totales, colWidths=[62 * mm, 28 * mm])
    totales.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_COLOR_ROW)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(_COLOR_TEAL)),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor(_COLOR_NAVY)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm),
            ]
        )
    )

    firmada = bool(evaluacion.firma_hash)
    if firmada:
        titulo = "FIRMA DIGITAL DE CONFORMIDAD" if evaluacion.estado == Evaluacion.Estado.CERRADA else "FIRMA DIGITAL CON OBSERVACIÓN"
        color_box = colors.HexColor("#6ee7b7") if evaluacion.estado == Evaluacion.Estado.CERRADA else colors.HexColor("#fcd34d")
        bg = colors.HexColor(_COLOR_OK_BG) if evaluacion.estado == Evaluacion.Estado.CERRADA else colors.HexColor(_COLOR_WARN_BG)
        contenido_firma = [
            P(titulo, estilo_firma_titulo),
            P(_nombre_persona(evaluacion.evaluado), estilo_firma_nombre),
            P("NOMBRE, FIRMA DIGITAL Y FECHA", estilo_firma_cap),
            Spacer(1, 2 * mm),
            P(_texto_dt(evaluacion.firmada_en), estilo_firma_dato),
            Paragraph(
                f"SHA-256<br/>{_escape(_hash_en_lineas(evaluacion.firma_hash))}",
                estilo_hash,
            ),
        ]
        if evaluacion.ip_firma:
            contenido_firma.append(P(f"IP de firma: {evaluacion.ip_firma}", estilo_firma_dato))
        if (evaluacion.comentario_empleado_cierre or "").strip():
            contenido_firma.append(Spacer(1, 1.5 * mm))
            contenido_firma.append(
                P(f"Observación: {evaluacion.comentario_empleado_cierre}", estilo_firma_dato)
            )
    else:
        color_box = colors.HexColor(_COLOR_LINE)
        bg = colors.white
        contenido_firma = [
            P("PENDIENTE DE FIRMA DIGITAL", estilo_firma_pendiente),
            P(_nombre_persona(evaluacion.evaluado), estilo_firma_nombre),
            P("NOMBRE, FIRMA DIGITAL Y FECHA", estilo_firma_cap),
            Spacer(1, 2 * mm),
            P("El evaluado todavía no registró la conformidad.", estilo_firma_dato),
        ]

    firma = Table([[contenido_firma]], colWidths=[86 * mm])
    firma.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.9, color_box),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )

    fila = Table([[totales, firma]], colWidths=[92 * mm, 90 * mm])
    fila.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (0, 0), "BOTTOM"),
                ("VALIGN", (1, 0), (1, 0), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 2 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    if firmada:
        legal = (
            "Este documento es el registro oficial de la evaluación de desempeño. "
            "La firma digital SHA-256 acredita que el evaluado leyó el resultado y "
            "registró su conformidad (o su observación) en TeamPulse. Cualquier "
            "alteración del contenido invalidaría el código de verificación."
        )
    else:
        legal = (
            "Documento preliminar generado por TeamPulse. No sustituye el comprobante "
            "firmado: la firma digital del evaluado todavía no fue registrada."
        )
    return KeepTogether(
        [
            fila,
            Spacer(1, 4 * mm),
            P(legal, estilo_legal),
        ]
    )


def _banda(titulo: str, estilo_seccion):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    tabla = Table(
        [[Paragraph(_escape(titulo), estilo_seccion)]],
        colWidths=[182 * mm],
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_COLOR_NAVY)),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    return tabla


_LOGO_PNG: bytes | None = None
_LOGO_CACHE_LISTO = False


def _flowable_logo(lado):
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image

    png = _logo_png_bytes()
    if not png:
        return None
    try:
        return Image(ImageReader(BytesIO(png)), width=lado, height=lado, kind="proportional")
    except Exception:
        return None


def _logo_path() -> str | None:
    for nombre in ("logo_solo.png", "logo.png"):
        encontrado = find(nombre)
        if encontrado:
            return encontrado
        candidato = Path(settings.BASE_DIR) / "theme" / "static" / nombre
        if candidato.exists():
            return str(candidato)
    return None


def _logo_png_bytes() -> bytes | None:
    global _LOGO_PNG, _LOGO_CACHE_LISTO
    if _LOGO_CACHE_LISTO:
        return _LOGO_PNG
    _LOGO_CACHE_LISTO = True
    path = _logo_path()
    if not path:
        _LOGO_PNG = None
        return None
    try:
        _LOGO_PNG = _preparar_logo(path)
    except Exception:
        _LOGO_PNG = None
    return _LOGO_PNG


def _preparar_logo(path: str) -> bytes:
    from PIL import Image as PILImage

    img = PILImage.open(path)
    img.thumbnail((240, 240), PILImage.Resampling.LANCZOS)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    pixeles = img.getdata()
    limpios = []
    for r, g, b, a in pixeles:
        if r < 28 and g < 28 and b < 28:
            limpios.append((r, g, b, 0))
        else:
            limpios.append((r, g, b, a))
    img.putdata(limpios)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _promedio_ponderado(items, campo) -> Decimal | None:
    num = Decimal("0")
    den = Decimal("0")
    for item in items:
        puntaje = getattr(item, campo)
        pond = getattr(item.criterio, "ponderacion", None) or Decimal("0")
        if puntaje is None or pond <= 0:
            continue
        num += Decimal(puntaje) * pond
        den += pond
    if den <= 0:
        return None
    return (num / den).quantize(Decimal("0.01"))


def _hash_en_lineas(valor: str) -> str:
    texto = (valor or "").strip()
    if len(texto) <= 32:
        return texto
    return f"{texto[:32]}\n{texto[32:]}"


def _nombre_persona(usuario) -> str:
    if usuario is None:
        return "—"
    nombre = (usuario.get_full_name() or "").strip()
    return nombre or getattr(usuario, "email", None) or "—"


def _texto_fecha(valor) -> str:
    if valor is None:
        return "—"
    from datetime import datetime

    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        return date_format(valor, "d/m/Y")
    return date_format(valor, "d/m/Y")


def _texto_dt(valor) -> str:
    if valor is None:
        return "—"
    from datetime import datetime

    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        return date_format(valor, "d/m/Y H:i")
    return date_format(valor, "d/m/Y")


def _texto_timestamp(valor) -> str:
    if valor is None:
        valor = timezone.localtime(timezone.now())
    from datetime import datetime

    if isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return date_format(valor, "d/m/Y H:i")


def _fmt_entero(valor) -> str:
    if valor is None:
        return "—"
    return str(valor)


def _fmt_decimal(valor) -> str:
    if valor is None:
        return "—"
    texto = f"{Decimal(valor):.2f}".replace(".", ",")
    return texto


def _fmt_promedio(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    return _fmt_decimal(valor)


def _fmt_brecha_prom(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    texto = _fmt_decimal(valor)
    if valor > 0:
        return f"+{texto}"
    return texto


def _escape(texto) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
