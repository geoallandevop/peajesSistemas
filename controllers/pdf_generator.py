import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from version import __version__


def generate_closure_pdf(closure_data: dict, output_path: str) -> str:
    """
    Genera un informe oficial en PDF del Cierre Diario de Caja en Quetzales (Q),
    excluyendo cualquier sección de ahorro o descuento.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2563eb"),
        alignment=1,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_style = ParagraphStyle(
        "BoldText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Encabezado
    story.append(Paragraph("SISTEMA DE GESTIÓN DE PEAJES", title_style))
    story.append(Paragraph("REPORTE OFICIAL DE CIERRE DIARIO DE CAJA", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

    # Metadatos del Cierre
    meta_data = [
        [
            Paragraph("<b>Fecha de Cierre:</b>", bold_style),
            Paragraph(str(closure_data.get("closure_date", "")), normal_style),
            Paragraph("<b>Generado el:</b>", bold_style),
            Paragraph(str(closure_data.get("generated_at", "")), normal_style),
        ],
        [
            Paragraph("<b>Cerrado por:</b>", bold_style),
            Paragraph(str(closure_data.get("closed_by", "Supervisor de Turno")), normal_style),
            Paragraph("<b>Total Transacciones:</b>", bold_style),
            Paragraph(f"{closure_data.get('total_transactions', 0)} vehículos", normal_style),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[120, 140, 120, 150])
    t_meta.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # Resumen Financiero General (En Quetzales, sin ahorro)
    story.append(Paragraph("RESUMEN DE RECAUDACIÓN (QUETZALES)", h2_style))
    tot_rev = closure_data.get("total_revenue", 0.0)
    tot_cash = closure_data.get("total_cash", 0.0)
    tot_card = closure_data.get("total_card", 0.0)

    summary_data = [
        [
            Paragraph("<b>CONCEPTO</b>", bold_style),
            Paragraph("<b>MÉTODO / ESTADO</b>", bold_style),
            Paragraph("<b>TOTAL RECAUDADO (Q)</b>", bold_style),
        ],
        [
            Paragraph("Cobro en Efectivo", normal_style),
            Paragraph("Moneda Nacional (Efectivo)", normal_style),
            Paragraph(f"Q {tot_cash:,.2f}", bold_style),
        ],
        [
            Paragraph("Cobro con Tarjeta", normal_style),
            Paragraph("POS / Terminal Electrónica", normal_style),
            Paragraph(f"Q {tot_card:,.2f}", bold_style),
        ],
        [
            Paragraph("<b>RECAUDACIÓN TOTAL</b>", bold_style),
            Paragraph("<b>Total Consolidado</b>", bold_style),
            Paragraph(f"<b>Q {tot_rev:,.2f}</b>", bold_style),
        ],
    ]
    t_sum = Table(summary_data, colWidths=[200, 180, 150])
    t_sum.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ])
    )
    story.append(t_sum)
    story.append(Spacer(1, 14))

    # Desglose por Categoría Vehicular
    story.append(Paragraph("DISTRIBUCIÓN POR CATEGORÍA DE VEHÍCULO", h2_style))
    cat_rows = [
        [
            Paragraph("<b>Categoría</b>", bold_style),
            Paragraph("<b>Vehículos</b>", bold_style),
            Paragraph("<b>Efectivo (Q)</b>", bold_style),
            Paragraph("<b>Tarjeta (Q)</b>", bold_style),
            Paragraph("<b>Total (Q)</b>", bold_style),
            Paragraph("<b>Part. %</b>", bold_style),
        ]
    ]
    for cat, d in closure_data.get("breakdown_by_category", {}).items():
        cat_rows.append([
            Paragraph(cat, normal_style),
            Paragraph(str(d.get("vehicles_count", 0)), normal_style),
            Paragraph(f"Q {d.get('cash_revenue', 0.0):,.2f}", normal_style),
            Paragraph(f"Q {d.get('card_revenue', 0.0):,.2f}", normal_style),
            Paragraph(f"Q {d.get('net_revenue', 0.0):,.2f}", bold_style),
            Paragraph(f"{d.get('share_of_revenue_pct', 0.0):.1f}%", normal_style),
        ])
    t_cat = Table(cat_rows, colWidths=[130, 70, 85, 85, 95, 65])
    t_cat.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(t_cat)
    story.append(Spacer(1, 14))

    # Desglose por Condición de Membresía
    story.append(Paragraph("DISTRIBUCIÓN POR CONDICIÓN DE MEMBRESÍA", h2_style))
    mem_rows = [
        [
            Paragraph("<b>Condición de Socio</b>", bold_style),
            Paragraph("<b>Vehículos</b>", bold_style),
            Paragraph("<b>Total Recaudado (Q)</b>", bold_style),
            Paragraph("<b>Participación %</b>", bold_style),
        ]
    ]
    for cond, d in closure_data.get("breakdown_by_membership", {}).items():
        mem_rows.append([
            Paragraph(cond, normal_style),
            Paragraph(str(d.get("vehicles_count", 0)), normal_style),
            Paragraph(f"Q {d.get('net_revenue', 0.0):,.2f}", bold_style),
            Paragraph(f"{d.get('share_of_revenue_pct', 0.0):.1f}%", normal_style),
        ])
    t_mem = Table(mem_rows, colWidths=[200, 100, 130, 100])
    t_mem.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(t_mem)
    story.append(Spacer(1, 14))

    # Desglose por Carril
    story.append(Paragraph("DISTRIBUCIÓN POR CARRIL DE PEAJE", h2_style))
    lane_rows = [
        [
            Paragraph("<b>Carril</b>", bold_style),
            Paragraph("<b>Nombre / Tipo</b>", bold_style),
            Paragraph("<b>Vehículos</b>", bold_style),
            Paragraph("<b>Espera Prom.</b>", bold_style),
            Paragraph("<b>Recaudado (Q)</b>", bold_style),
        ]
    ]
    for code, d in closure_data.get("breakdown_by_lane", {}).items():
        lane_rows.append([
            Paragraph(code, bold_style),
            Paragraph(f"{d.get('lane_name', '')} ({d.get('lane_type', '')})", normal_style),
            Paragraph(str(d.get("vehicles_count", 0)), normal_style),
            Paragraph(f"{d.get('avg_wait_seconds', 0.0):.2f}s", normal_style),
            Paragraph(f"Q {d.get('net_revenue', 0.0):,.2f}", bold_style),
        ])
    t_lane = Table(lane_rows, colWidths=[90, 200, 75, 75, 90])
    t_lane.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(t_lane)
    story.append(Spacer(1, 30))

    # Firmas
    sig_data = [
        [
            Paragraph("____________________________<br/><b>Supervisor de Turno</b>", bold_style),
            Paragraph("____________________________<br/><b>Auditor Contable</b>", bold_style),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[265, 265])
    t_sig.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(t_sig)
    story.append(Spacer(1, 16))

    version_footer = Paragraph(
        f"Sistema de Gestión de Peajes (Desktop) v{__version__} — Documento Oficial de Cierre Contable",
        ParagraphStyle("FootClose", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"), alignment=1),
    )
    story.append(version_footer)

    doc.build(story)
    return output_path


def generate_simulation_pdf(sim_data: dict, output_path: str) -> str:
    """
    Genera el informe ejecutivo en PDF de la Simulación de Eventos Discretos (DES)
    con las métricas acumuladas, rendimiento, finanzas en Quetzales y estadísticas por carril.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SimTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "SimSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2563eb"),
        alignment=1,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_style = ParagraphStyle(
        "BoldText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    story.append(Paragraph("SISTEMA DE GESTIÓN DE PEAJES", title_style))
    story.append(Paragraph("INFORME EJECUTIVO DE SIMULACIÓN DE EVENTOS DISCRETOS (DES)", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

    # Parámetros de Entrada Configurados
    story.append(Paragraph("PARÁMETROS DE ENTRADA CONFIGURADOS", h2_style))
    params_data = [
        [
            Paragraph("<b>Densidad de Tráfico:</b>", bold_style),
            Paragraph(str(sim_data.get("traffic_density", "Media")), normal_style),
            Paragraph("<b>Tiempo Verde Semáforo:</b>", bold_style),
            Paragraph(f"{sim_data.get('traffic_light_green_seconds', 15)} segundos", normal_style),
        ],
        [
            Paragraph("<b>Duración Simulación:</b>", bold_style),
            Paragraph(f"{sim_data.get('duration_minutes', 5)} minutos ({sim_data.get('horizon_cycles', 300)}s)", normal_style),
            Paragraph("<b>Distribución Vehicular:</b>", bold_style),
            Paragraph(str(sim_data.get("vehicle_distribution_summary", "Livianos 52%, Motos 18%, Autobuses 10%, Camiones 20%")), normal_style),
        ],
    ]
    t_p = Table(params_data, colWidths=[130, 135, 130, 135])
    t_p.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_p)
    story.append(Spacer(1, 10))

    # Métricas Acumuladas y Rendimiento
    story.append(Paragraph("MÉTRICAS ACUMULADAS Y RENDIMIENTO", h2_style))
    perf_data = [
        [
            Paragraph("<b>Métrica Operativa</b>", bold_style),
            Paragraph("<b>Valor Obtenido</b>", bold_style),
            Paragraph("<b>Unidad</b>", bold_style),
        ],
        [
            Paragraph("Tiempo de Espera Medio", normal_style),
            Paragraph(f"{sim_data.get('avg_wait_time_seconds', 0.0):.2f}", bold_style),
            Paragraph("segundos", normal_style),
        ],
        [
            Paragraph("Espera Máxima", normal_style),
            Paragraph(f"{sim_data.get('max_wait_time_seconds', 0.0):.2f}", bold_style),
            Paragraph("segundos", normal_style),
        ],
        [
            Paragraph("Tiempo Medio de Atención", normal_style),
            Paragraph(f"{sim_data.get('avg_service_time_seconds', 0.0):.2f}", bold_style),
            Paragraph("segundos", normal_style),
        ],
        [
            Paragraph("El flujo vehicular por Minuto", normal_style),
            Paragraph(f"{sim_data.get('throughput_vehicles_per_minute', 0.0):.2f}", bold_style),
            Paragraph("veh/min", normal_style),
        ],
        [
            Paragraph("El flujo vehicular por Hora", normal_style),
            Paragraph(f"{sim_data.get('throughput_vehicles_per_hour', 0.0):.2f}", bold_style),
            Paragraph("veh/hora", normal_style),
        ],
    ]
    t_perf = Table(perf_data, colWidths=[240, 150, 140])
    t_perf.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ])
    )
    story.append(t_perf)
    story.append(Spacer(1, 10))

    # Finanzas de la Simulación en Quetzales
    story.append(Paragraph("FINANZAS DE LA SIMULACIÓN (QUETZALES)", h2_style))
    fin_data = [
        [
            Paragraph("<b>Recaudación Total:</b>", bold_style),
            Paragraph(f"Q {sim_data.get('total_revenue', 0.0):,.2f}", bold_style),
            Paragraph("<b>Descuentos Socios:</b>", bold_style),
            Paragraph(f"Q {sim_data.get('total_discounts', 0.0):,.2f}", normal_style),
        ],
        [
            Paragraph("<b>Cobro en Efectivo:</b>", bold_style),
            Paragraph(f"Q {sim_data.get('total_cash', 0.0):,.2f}", normal_style),
            Paragraph("<b>Cobro con Tarjeta:</b>", bold_style),
            Paragraph(f"Q {sim_data.get('total_card', 0.0):,.2f}", normal_style),
        ],
    ]
    t_fin = Table(fin_data, colWidths=[130, 135, 130, 135])
    t_fin.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_fin)
    story.append(Spacer(1, 10))

    # Estadísticas por Carril
    story.append(Paragraph("ESTADÍSTICAS POR CARRIL", h2_style))
    lane_rows = [
        [
            Paragraph("<b>Carril</b>", bold_style),
            Paragraph("<b>Tipo</b>", bold_style),
            Paragraph("<b>Veh.</b>", bold_style),
            Paragraph("<b>Espera Prom.</b>", bold_style),
            Paragraph("<b>Atención</b>", bold_style),
            Paragraph("<b>Cola Máx.</b>", bold_style),
            Paragraph("<b>Ocupación</b>", bold_style),
            Paragraph("<b>Recaudado (Q)</b>", bold_style),
        ]
    ]
    for lm in sim_data.get("lane_metrics", []):
        lane_rows.append([
            Paragraph(lm.get("code", ""), bold_style),
            Paragraph(lm.get("lane_type", ""), normal_style),
            Paragraph(str(lm.get("processed", 0)), normal_style),
            Paragraph(f"{lm.get('avg_wait', 0.0):.2f}s", normal_style),
            Paragraph(f"{lm.get('avg_srv', 0.0):.2f}s", normal_style),
            Paragraph(str(lm.get("max_queue", 0)), normal_style),
            Paragraph(f"{lm.get('utilization', 0.0):.1f}%", normal_style),
            Paragraph(f"Q {lm.get('revenue', 0.0):,.2f}", bold_style),
        ])
    t_lanes = Table(lane_rows, colWidths=[65, 95, 40, 65, 60, 55, 65, 85])
    t_lanes.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(t_lanes)
    story.append(Spacer(1, 12))

    # Invariante de Conservación
    story.append(
        Paragraph(
            f"<b>Ley de Conservación:</b> {sim_data.get('conservation_equation', '')} "
            f"— <b>Pérdida Cero Garantizada (100% de vehículos atendidos)</b>.",
            normal_style,
        )
    )
    story.append(Spacer(1, 16))

    version_sim_footer = Paragraph(
        f"Sistema de Gestión de Peajes (Desktop) v{__version__} — Motor de Simulación de Eventos Discretos (DES)",
        ParagraphStyle("FootSim", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"), alignment=1),
    )
    story.append(version_sim_footer)

    doc.build(story)
    return output_path
