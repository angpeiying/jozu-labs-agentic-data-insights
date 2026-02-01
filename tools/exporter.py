# tools/exporter.py
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


def _safe(x: Any, fallback: str = "—") -> str:
    if x is None:
        return fallback
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False, indent=2)
    return str(x)


def report_to_markdown(report: Dict[str, Any]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    insights = report.get("insights", []) if isinstance(report.get("insights"), list) else []
    dq = report.get("data_quality_notes", []) if isinstance(report.get("data_quality_notes"), list) else []
    next_steps = report.get("next_steps", []) if isinstance(report.get("next_steps"), list) else []

    pack_results = report.get("pack_results", {}) if isinstance(report.get("pack_results"), dict) else {}
    snap = pack_results.get("snapshot", {}) if isinstance(pack_results.get("snapshot"), dict) else {}
    shape = snap.get("shape", {}) if isinstance(snap.get("shape"), dict) else {}

    lines: List[str] = []
    lines.append(f"# Jozu Labs Analytics Report")
    lines.append(f"- Generated: {ts}")
    if report.get("profiling_report_url"):
        lines.append(f"- Profiling: {report['profiling_report_url']}")
    lines.append("")

    lines.append("## Overview")
    lines.append(_safe(summary.get("dataset_overview", "No overview provided.")))
    lines.append("")
    lines.append("### Snapshot")
    lines.append(f"- Rows: {_safe(shape.get('rows'))}")
    lines.append(f"- Columns: {_safe(shape.get('cols'))}")
    lines.append(f"- Duplicate rows: {_safe(snap.get('duplicate_rows'))}")
    lines.append("")

    lines.append("## Key Risks")
    for r in (summary.get("key_risks") or [])[:10]:
        lines.append(f"- {_safe(r)}")
    if not (summary.get("key_risks") or []):
        lines.append("- —")
    lines.append("")

    lines.append("## Opportunities")
    for o in (summary.get("key_opportunities") or [])[:10]:
        lines.append(f"- {_safe(o)}")
    if not (summary.get("key_opportunities") or []):
        lines.append("- —")
    lines.append("")

    lines.append("## Data Quality Notes")
    if dq:
        for n in dq[:10]:
            if isinstance(n, dict):
                lines.append(
                    f"- **{_safe(n.get('issue'))}** | Columns: {_safe(n.get('columns'))} | Impact: {_safe(n.get('impact'))}"
                )
                lines.append(f"  - Suggestion: {_safe(n.get('suggestion'))}")
            else:
                lines.append(f"- {_safe(n)}")
    else:
        lines.append("- —")
    lines.append("")

    lines.append("## Insights")
    if insights:
        for ins in insights[:20]:
            if not isinstance(ins, dict):
                lines.append(f"- {_safe(ins)}")
                continue
            title = _safe(ins.get("title", "Untitled"))
            sev = _safe(ins.get("severity", "info"))
            conf = ins.get("confidence")
            conf_str = f"{int(conf * 100)}%" if isinstance(conf, (int, float)) else "—"
            lines.append(f"### {title}")
            lines.append(f"- Severity: **{sev}**")
            lines.append(f"- Confidence: **{conf_str}**")
            lines.append(f"- Description: {_safe(ins.get('description'))}")
            lines.append(f"- Action: {_safe(ins.get('recommended_action'))}")
            lines.append("")
    else:
        lines.append("- —")
        lines.append("")

    lines.append("## Next Steps")
    if next_steps:
        for s in next_steps[:15]:
            lines.append(f"- {_safe(s)}")
    else:
        lines.append("- —")
    lines.append("")

    errs = report.get("errors", [])
    if isinstance(errs, list) and errs:
        lines.append("## Errors / Warnings")
        for e in errs[:30]:
            lines.append(f"- {_safe(e)}")
        lines.append("")

    return "\n".join(lines)


# ----------------------------
# NEW: premium PDF layout
# ----------------------------
def report_to_pdf_bytes(report: Dict[str, Any], *, job_id: Optional[str] = None) -> bytes:
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.60 * inch,
        bottomMargin=0.60 * inch,
        title="Jozu Labs Analytics Report",
        author="Jozu Labs",
    )

    styles = getSampleStyleSheet()

    # Monochrome “modern” styles
    H1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.black,
        spaceAfter=6,
    )
    H2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=6,
    )
    BODY = ParagraphStyle(
        "BODY",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.black,
    )
    MUTED = ParagraphStyle(
        "MUTED",
        parent=BODY,
        textColor=colors.HexColor("#555555"),
    )
    SMALL = ParagraphStyle(
        "SMALL",
        parent=BODY,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#444444"),
    )

    def hr():
        return HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#DDDDDD"))

    def fmt(v: Any) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.4g}"
        return str(v)

    def sev_norm(s: Any) -> str:
        s = (s or "info")
        s = str(s).lower()
        return s if s in {"risk", "warning", "opportunity", "info"} else "info"

    story: List[Any] = []

    # ---- Header ----
    story.append(Paragraph("Jozu Labs — Analytics Report", H1))

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    left = Paragraph(f"<b>Generated:</b> {ts}", MUTED)
    right = Paragraph(f"<b>Job:</b> {fmt(job_id)}" if job_id else "", MUTED)
    meta = Table([[left, right]], colWidths=["70%", "30%"])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta)
    story.append(hr())
    story.append(Spacer(1, 12))

    # ---- Pull fields from report ----
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    insights = report.get("insights") if isinstance(report.get("insights"), list) else []
    dq = report.get("data_quality_notes") if isinstance(report.get("data_quality_notes"), list) else []
    next_steps = report.get("next_steps") if isinstance(report.get("next_steps"), list) else []
    errs = report.get("errors") if isinstance(report.get("errors"), list) else []

    pack_results = report.get("pack_results") if isinstance(report.get("pack_results"), dict) else {}
    snap = pack_results.get("snapshot") if isinstance(pack_results.get("snapshot"), dict) else {}
    shape = snap.get("shape") if isinstance(snap.get("shape"), dict) else {}

    # ---- Executive summary ----
    story.append(Paragraph("Executive Summary", H2))
    overview = summary.get("dataset_overview") or "—"
    story.append(Paragraph(fmt(overview), BODY))

    profiling_url = report.get("profiling_report_url")
    if profiling_url:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Profiling report:</b> {fmt(profiling_url)}", SMALL))

    story.append(Spacer(1, 12))

    # ---- Metrics grid ----
    story.append(Paragraph("Key Metrics", H2))
    rows = shape.get("rows")
    cols = shape.get("cols")
    dups = snap.get("duplicate_rows")
    insight_count = len(insights) if isinstance(insights, list) else 0

    metrics = [
        ["Rows", fmt(rows), "Columns", fmt(cols)],
        ["Duplicate rows", fmt(dups), "Insights", fmt(insight_count)],
    ]
    metrics_tbl = Table(metrics, colWidths=["22%", "28%", "22%", "28%"])
    metrics_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F6F6F6")),
                ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#DDDDDD")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#DDDDDD")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(metrics_tbl)
    story.append(Spacer(1, 14))

    # ---- Risks & Opportunities (compact) ----
    risks = summary.get("key_risks") or []
    opps = summary.get("key_opportunities") or []
    story.append(Paragraph("Risks & Opportunities", H2))

    def bullets(items: List[Any], limit: int = 6) -> Paragraph:
        if not items:
            return Paragraph("—", MUTED)
        s = "<br/>".join([f"• {fmt(x)}" for x in items[:limit]])
        return Paragraph(s, BODY)

    ro_tbl = Table(
        [[Paragraph("<b>Key Risks</b>", BODY), Paragraph("<b>Opportunities</b>", BODY)],
         [bullets(risks), bullets(opps)]],
        colWidths=["50%", "50%"],
    )
    ro_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#DDDDDD")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#DDDDDD")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F6F6F6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(ro_tbl)
    story.append(Spacer(1, 14))

    # ---- Data quality notes ----
    story.append(Paragraph("Data Quality Notes", H2))
    if not dq:
        story.append(Paragraph("—", MUTED))
    else:
        for n in dq[:8]:
            if isinstance(n, dict):
                issue = fmt(n.get("issue") or "Issue")
                cols_ = n.get("columns") or []
                impact = fmt(n.get("impact"))
                suggestion = fmt(n.get("suggestion"))
                block = (
                    f"<b>{issue}</b><br/>"
                    f"<font color='#555555'>"
                    f"<b>Columns:</b> {fmt(', '.join(cols_))}<br/>"
                    f"<b>Impact:</b> {impact}<br/>"
                    f"<b>Suggestion:</b> {suggestion}"
                    f"</font>"
                )
                story.append(Paragraph(block, BODY))
                story.append(Spacer(1, 8))
            else:
                story.append(Paragraph(f"• {fmt(n)}", BODY))
    story.append(Spacer(1, 10))

    # ---- Insights (cards) ----
    story.append(Paragraph("Insights", H2))
    if not insights:
        story.append(Paragraph("No insights were generated.", MUTED))
    else:
        for i, ins in enumerate(insights[:20], start=1):
            if not isinstance(ins, dict):
                story.append(Paragraph(f"• {fmt(ins)}", BODY))
                story.append(Spacer(1, 8))
                continue

            title = fmt(ins.get("title") or f"Insight {i}")
            sev = sev_norm(ins.get("severity"))
            conf = ins.get("confidence")
            conf_txt = "—"
            try:
                if isinstance(conf, (int, float)):
                    conf_txt = f"{float(conf)*100:.0f}%"
            except Exception:
                pass

            desc = fmt(ins.get("description") or "—")
            action = fmt(ins.get("recommended_action") or "—")

            # Simple monochrome tag line
            tag = f"<b>{sev.upper()}</b> &nbsp;&nbsp;<font color='#555555'>Confidence: {conf_txt}</font>"

            card = Table(
                [
                    [Paragraph(f"<b>{title}</b>", BODY)],
                    [Paragraph(tag, SMALL)],
                    [Paragraph(desc, BODY)],
                    [Paragraph(f"<font color='#555555'><b>Action:</b> {action}</font>", BODY)],
                ],
                colWidths=["100%"],
            )
            card.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#DDDDDD")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(KeepTogether([card, Spacer(1, 10)]))

    # ---- Next steps ----
    if next_steps:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Next Steps", H2))
        s = "<br/>".join([f"• {fmt(x)}" for x in next_steps[:12]])
        story.append(Paragraph(s, BODY))

    # ---- Errors ----
    if errs:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Errors / Warnings", H2))
        s = "<br/>".join([f"• {fmt(x)}" for x in errs[:18]])
        story.append(Paragraph(s, BODY))

    # Page footer
    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.65 * inch, 0.45 * inch, "Jozu Labs")
        canvas.drawRightString(LETTER[0] - 0.65 * inch, 0.45 * inch, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    return buf.getvalue()
