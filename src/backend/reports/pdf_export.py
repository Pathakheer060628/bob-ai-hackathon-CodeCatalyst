"""Renders a completed run result into a one-click operator brief PDF."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(run_id: str, result: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18)
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story = [
        Paragraph("GridSentinel — Operator Optimisation Brief", title_style),
        Paragraph(f"Run ID: {run_id}", body_style),
        Spacer(1, 0.2 * inch),
    ]

    verification = result["verification"]
    badge_color = colors.HexColor("#1a7f37") if verification["trusted"] else colors.HexColor("#c0392b")
    badge_text = "VERIFIED — every number traces to computed state" if verification["trusted"] else "UNVERIFIED NUMBERS FLAGGED"
    story.append(Paragraph(f'<font color="{badge_color.hexval()}"><b>{badge_text}</b></font>', body_style))
    story.append(Spacer(1, 0.2 * inch))

    for paragraph in result["narrative"].split("\n\n"):
        text = paragraph.replace("**", "").replace("\n", "<br/>")
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 0.12 * inch))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Curtailment Minimization Summary", heading_style))
    curtailment = result["curtailment"]
    table_data = [
        ["Metric", "Value"],
        ["Baseline curtailment (no flexibility)", f"{curtailment['baseline_curtailed_mwh']:,.1f} MWh"],
        ["Optimized plan curtailment", f"{curtailment['optimized_curtailed_mwh']:,.1f} MWh"],
        ["Curtailment avoided", f"{curtailment['curtailment_avoided_mwh']:,.1f} MWh"],
        ["Reduction", f"{curtailment['curtailment_reduction_pct']:.1f}%"],
    ]
    table = Table(table_data, colWidths=[3.2 * inch, 2.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Renewable Anomalies & Root Causes", heading_style))
    if result["anomalies"]:
        anomaly_rows = [["Asset", "Direction", "Duration (h)", "Root Cause"]]
        for a in result["anomalies"]:
            anomaly_rows.append([a["asset"], a["direction"], str(a["duration_hours"]), a["label"]])
        anomaly_table = Table(anomaly_rows, colWidths=[1.1 * inch, 0.9 * inch, 0.9 * inch, 2.8 * inch])
        anomaly_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(anomaly_table)
    else:
        story.append(Paragraph("No sustained anomalies detected in this window.", body_style))

    doc.build(story)
    return buffer.getvalue()
