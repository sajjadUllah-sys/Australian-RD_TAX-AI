from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
import os

BRAND_BLUE = colors.HexColor("#1a3c6e")
BRAND_LIGHT = colors.HexColor("#e8f0fb")
BRAND_ACCENT = colors.HexColor("#2e6fcc")
GRAY = colors.HexColor("#f5f5f5")
DARK_GRAY = colors.HexColor("#444444")


def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontSize=26, textColor=colors.white,
        fontName="Helvetica-Bold", leading=32, spaceAfter=8
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", fontSize=13, textColor=colors.HexColor("#ccd9f0"),
        fontName="Helvetica", leading=18
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading", fontSize=13, textColor=colors.white,
        fontName="Helvetica-Bold", leading=16,
        backColor=BRAND_BLUE, leftIndent=-12, rightIndent=-12,
        borderPadding=(6, 12, 6, 12), spaceAfter=10, spaceBefore=16
    )
    styles["sub_heading"] = ParagraphStyle(
        "sub_heading", fontSize=11, textColor=BRAND_BLUE,
        fontName="Helvetica-Bold", leading=14,
        spaceBefore=10, spaceAfter=4
    )
    styles["label"] = ParagraphStyle(
        "label", fontSize=9, textColor=BRAND_ACCENT,
        fontName="Helvetica-Bold", leading=12, spaceAfter=2
    )
    styles["body"] = ParagraphStyle(
        "body", fontSize=10, textColor=DARK_GRAY,
        fontName="Helvetica", leading=15, spaceAfter=6
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontSize=10, textColor=DARK_GRAY,
        fontName="Helvetica", leading=14, leftIndent=14,
        bulletIndent=4, spaceAfter=3
    )
    styles["score_band"] = ParagraphStyle(
        "score_band", fontSize=11, fontName="Helvetica-Bold",
        leading=14, textColor=BRAND_BLUE
    )
    styles["footer"] = ParagraphStyle(
        "footer", fontSize=8, textColor=colors.HexColor("#999999"),
        fontName="Helvetica", leading=10, alignment=TA_CENTER
    )
    return styles


def score_color(score, max_score):
    pct = score / max_score if max_score else 0
    if pct >= 0.8:
        return colors.HexColor("#1a7a4a")
    elif pct >= 0.65:
        return colors.HexColor("#2e6fcc")
    elif pct >= 0.5:
        return colors.HexColor("#d08000")
    else:
        return colors.HexColor("#c0392b")


def add_page_header(canvas, doc, company, project):
    canvas.saveState()
    canvas.setFillColor(BRAND_BLUE)
    canvas.rect(0, A4[1] - 36, A4[0], 36, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.5 * cm, A4[1] - 22, company)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - 1.5 * cm, A4[1] - 22, f"R&D Tax Incentive Plan — {project}")

    canvas.setFillColor(colors.HexColor("#cccccc"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}  |  Generated {datetime.now().strftime('%d %B %Y')}  |  Confidential")
    canvas.restoreState()


def build_cover(story, styles, data):
    story.append(Spacer(1, 3 * cm))

    cover_table = Table(
        [[Paragraph(data.get("report_title", "R&D Tax Incentive Plan"), styles["cover_title"]),
          Paragraph(f"Financial Year: {data.get('financial_year', '')}<br/>"
                    f"Prepared: {datetime.now().strftime('%d %B %Y')}", styles["cover_sub"])]],
        colWidths=[11 * cm, 7 * cm]
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 24),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 0.8 * cm))

    meta = [
        ["Company", data.get("company_name", "—")],
        ["ABN", data.get("abn", "—")],
        ["Project Title", data.get("project_title", "—")],
        ["Start Date", data.get("start_date", "—")],
        ["End Date", data.get("end_date", "—")],
        ["Industry / ANZSIC", data.get("anzsic", "—")],
        ["Budgeted R&D Spend", data.get("budget", "—")],
        ["Contact Person", data.get("contact_person", "—")],
    ]
    meta_table = Table(meta, colWidths=[5 * cm, 13 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(meta_table)
    story.append(PageBreak())


def build_score_section(story, styles, scoring):
    if not scoring:
        return
    story.append(Paragraph("RDTI Pre-Qualification Score", styles["section_heading"]))

    total = scoring.get("total", 0)
    outcome = scoring.get("outcome", "")
    outcome_color = score_color(total, 100)

    summary_table = Table(
        [[Paragraph(f"Total Score: {total}/100", styles["score_band"]),
          Paragraph(f"Outcome: {outcome}", styles["score_band"])]],
        colWidths=[9 * cm, 9 * cm]
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), outcome_color),
        ("TEXTCOLOR", (1, 0), (1, -1), outcome_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * cm))

    breakdown = scoring.get("breakdown", [])
    if breakdown:
        rows = [["Category", "Score", "Max"]]
        for item in breakdown:
            rows.append([item["category"], str(item["score"]), str(item["max"])])
        t = Table(rows, colWidths=[12 * cm, 3 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

    gaps = scoring.get("gaps", [])
    if gaps:
        story.append(Paragraph("Key Gaps Identified", styles["sub_heading"]))
        for g in gaps:
            story.append(Paragraph(f"• {g}", styles["bullet"]))

    recs = scoring.get("recommendations", [])
    if recs:
        story.append(Paragraph("Recommendations", styles["sub_heading"]))
        for r in recs:
            story.append(Paragraph(f"• {r}", styles["bullet"]))

    story.append(PageBreak())


def build_project_overview(story, styles, data):
    story.append(Paragraph("Part A — R&D Plan Overview", styles["section_heading"]))

    fields = [
        ("Project Objective", data.get("project_objective", "")),
        ("Record Keeping", data.get("record_keeping", "")),
        ("Know-how / IP Beneficiary", data.get("ip_beneficiary", "")),
    ]
    for label, value in fields:
        if value:
            story.append(Paragraph(label, styles["label"]))
            story.append(Paragraph(value or "—", styles["body"]))
            story.append(Spacer(1, 0.2 * cm))


def build_activities(story, styles, activities):
    for idx, act in enumerate(activities, 1):
        story.append(PageBreak())
        atype = act.get("type", "Core")
        title = act.get("title", f"Activity {idx}")
        story.append(Paragraph(f"{atype} R&D Activity — {title}", styles["section_heading"]))

        sections = [
            ("Description", act.get("description", "")),
            ("Hypothesis", act.get("hypothesis", "")),
            ("Sources Investigated", act.get("sources_investigated", "")),
            ("Why a Competent Professional Could Not Determine the Outcome", act.get("competent_professional", "")),
            ("Experiments Conducted", act.get("experiments", "")),
            ("Evaluation of Results", act.get("evaluation", "")),
            ("Conclusions", act.get("conclusions", "")),
            ("New Knowledge Generated", act.get("new_knowledge", "")),
            ("Evidence Kept", act.get("evidence", "")),
        ]

        if atype.lower() == "supporting":
            sections = [
                ("Description", act.get("description", "")),
                ("How This Directly Supports Core R&D", act.get("linkage", "")),
                ("Dominant Purpose Justification", act.get("dominant_purpose", "")),
                ("Evidence Kept", act.get("evidence", "")),
            ]

        for label, value in sections:
            if value and value.strip():
                story.append(Paragraph(label, styles["label"]))
                if "\n" in value:
                    for line in value.strip().split("\n"):
                        line = line.strip()
                        if line.startswith(("•", "-", "*")):
                            story.append(Paragraph(line, styles["bullet"]))
                        elif line:
                            story.append(Paragraph(line, styles["body"]))
                else:
                    story.append(Paragraph(value, styles["body"]))
                story.append(Spacer(1, 0.2 * cm))

        supporting = act.get("supporting_activities", [])
        if supporting:
            for sub in supporting:
                story.append(Spacer(1, 0.3 * cm))
                story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_LIGHT))
                story.append(Paragraph(f"Supporting Activity — {sub.get('title', '')}", styles["sub_heading"]))
                for slabel, skey in [
                    ("Description", "description"),
                    ("How This Supports Core R&D", "linkage"),
                    ("Dominant Purpose", "dominant_purpose"),
                    ("Evidence Kept", "evidence"),
                ]:
                    sval = sub.get(skey, "")
                    if sval and sval.strip():
                        story.append(Paragraph(slabel, styles["label"]))
                        story.append(Paragraph(sval, styles["body"]))
                        story.append(Spacer(1, 0.15 * cm))


def generate_pdf(data: dict, output_path: str) -> str:
    styles = build_styles()
    company = data.get("company_name", "Company")
    project = data.get("project_title", "R&D Project")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    build_cover(story, styles, data)
    build_score_section(story, styles, data.get("scoring"))
    build_project_overview(story, styles, data)

    activities = data.get("activities", [])
    if activities:
        build_activities(story, styles, activities)

    doc.build(
        story,
        onFirstPage=lambda c, d: add_page_header(c, d, company, project),
        onLaterPages=lambda c, d: add_page_header(c, d, company, project),
    )
    return output_path
