"""CV PDF renderer — reused cleanly from src/cv_generator.py (_render_pdf).

Output naming: output/cvs/CV_<Name>_<Company>.pdf
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#1b1b1f")
ACCENT = colors.HexColor("#b8860b")
GREY = colors.HexColor("#5a5a63")
LINE = colors.HexColor("#d8d6cf")

S = {
    "name": ParagraphStyle(
        "name",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=INK,
        leading=26,
        spaceAfter=1.5 * mm,
    ),
    "role": ParagraphStyle(
        "role",
        fontName="Helvetica",
        fontSize=10.5,
        textColor=ACCENT,
        spaceAfter=2 * mm,
    ),
    "contact": ParagraphStyle(
        "contact",
        fontName="Helvetica",
        fontSize=8.5,
        textColor=GREY,
        spaceAfter=1 * mm,
    ),
    "section": ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=INK,
        spaceBefore=4.5 * mm,
        spaceAfter=1 * mm,
    ),
    "body": ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9.3,
        textColor=INK,
        leading=13,
        spaceAfter=1 * mm,
    ),
    "bullet": ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=9.2,
        textColor=INK,
        leading=12.5,
        leftIndent=4.5 * mm,
        bulletIndent=1 * mm,
        spaceAfter=0.7 * mm,
    ),
    "job_head": ParagraphStyle(
        "job_head",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=INK,
        spaceBefore=1.6 * mm,
    ),
    "date": ParagraphStyle(
        "date",
        fontName="Helvetica",
        fontSize=8.8,
        textColor=GREY,
        alignment=TA_RIGHT,
    ),
    "skill_label": ParagraphStyle(
        "skill_label",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=INK,
        leading=12.5,
    ),
    "skill_value": ParagraphStyle(
        "skill_value",
        fontName="Helvetica",
        fontSize=9,
        textColor=GREY,
        leading=12.5,
    ),
}


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text or "unknown").strip("_")[:40]


def _section(title: str) -> list:
    return [
        Paragraph(title.upper(), S["section"]),
        HRFlowable(width="100%", thickness=0.7, color=LINE, spaceAfter=1.6 * mm),
    ]


def _head_row(left: str, right: str) -> Table:
    t = Table(
        [[Paragraph(left, S["job_head"]), Paragraph(right, S["date"])]],
        colWidths=["72%", "28%"],
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return t


def _strip_dashes(obj):
    if isinstance(obj, str):
        return obj.replace("\u2014", "-").replace("\u2013", "-")
    if isinstance(obj, list):
        return [_strip_dashes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _strip_dashes(v) for k, v in obj.items()}
    return obj


def render_cv_pdf(cv: dict, out_path: Path) -> None:
    """Render tailored CV dict to a single-page PDF (same layout as src/cv_generator)."""
    cv = _strip_dashes(cv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=14 * mm,
        bottomMargin=13 * mm,
    )
    el = []
    c = cv.get("contact", {})

    el.append(Paragraph(cv.get("name", "").upper(), S["name"]))
    el.append(Paragraph(cv.get("title", ""), S["role"]))
    contact_bits = [x for x in (c.get("location"), c.get("email"), c.get("phone")) if x]
    links = [x for x in (c.get("linkedin"), c.get("github"), c.get("website")) if x]
    el.append(Paragraph("   |   ".join(contact_bits), S["contact"]))
    if links:
        el.append(Paragraph("   |   ".join(links), S["contact"]))
    el.append(HRFlowable(width="100%", thickness=1.1, color=ACCENT, spaceBefore=1.5 * mm))

    if cv.get("summary"):
        el.extend(_section("Objective"))
        el.append(Paragraph(cv["summary"], S["body"]))

    if cv.get("experience"):
        el.extend(_section("Work Experience"))
        for exp in cv["experience"]:
            el.append(
                _head_row(
                    f"{exp.get('role', '')} | {exp.get('company', '')}",
                    exp.get("period", ""),
                )
            )
            for b in exp.get("bullets", []):
                el.append(Paragraph(b, S["bullet"], bulletText="•"))

    if cv.get("skills"):
        el.extend(_section("Skills"))
        rows = [
            [
                Paragraph(g.get("category", ""), S["skill_label"]),
                Paragraph(", ".join(g.get("items", [])), S["skill_value"]),
            ]
            for g in cv["skills"]
        ]
        t = Table(rows, colWidths=["24%", "76%"])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        el.append(t)

    if cv.get("projects"):
        el.extend(_section("Projects"))
        for p in cv["projects"]:
            tech = ", ".join(p.get("tech", []))
            el.append(Paragraph(f"<b>{p.get('name', '')}</b>", S["body"]))
            el.append(
                Paragraph(
                    f"{p.get('description', '')}"
                    + (f" <font color='#5a5a63' size='8'>[{tech}]</font>" if tech else ""),
                    S["bullet"],
                )
            )

    if cv.get("education"):
        el.extend(_section("Education"))
        for e in cv["education"]:
            el.append(
                _head_row(
                    f"{e.get('degree', '')} | {e.get('school', '')}",
                    e.get("period", "") or "",
                )
            )
            if e.get("detail"):
                el.append(Paragraph(e["detail"], S["bullet"]))

    if cv.get("languages"):
        el.extend(_section("Languages"))
        el.append(Paragraph(", ".join(cv["languages"]), S["body"]))

    doc.build(el)


def cv_output_path(name: str, company: str, cv_dir: Path) -> Path:
    return cv_dir / f"CV_{safe_filename(name)}_{safe_filename(company)}.pdf"


# --- Cover letter PDF (from src/cover_letter.py) ---

_CL = {
    "header": ParagraphStyle(
        "cl_header",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=INK,
        spaceAfter=2 * mm,
    ),
    "meta": ParagraphStyle(
        "cl_meta",
        fontName="Helvetica",
        fontSize=9,
        textColor=GREY,
        leading=12,
        spaceAfter=1 * mm,
    ),
    "body": ParagraphStyle(
        "cl_body",
        fontName="Helvetica",
        fontSize=10.5,
        textColor=INK,
        leading=15,
        spaceAfter=3 * mm,
    ),
}


def render_cover_pdf(data: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    el = []
    name = data.get("candidate_name") or "Natnael Eskinder Mengistu"
    el.append(Paragraph(name, _CL["header"]))
    contact = data.get("contact_line") or ""
    if contact:
        el.append(Paragraph(contact.replace("\n", "<br/>"), _CL["meta"]))
    el.append(Spacer(1, 4 * mm))
    date = data.get("date") or ""
    if date:
        el.append(Paragraph(date, _CL["meta"]))
    el.append(Spacer(1, 3 * mm))
    greeting = data.get("greeting") or "Dear Hiring Team,"
    el.append(Paragraph(greeting, _CL["body"]))
    for para in data.get("paragraphs") or []:
        text = str(para).replace("\n", " ").strip()
        if text:
            el.append(Paragraph(text, _CL["body"]))
    closing = data.get("closing") or "Sincerely,"
    el.append(Paragraph(closing, _CL["body"]))
    el.append(Paragraph(name, _CL["body"]))
    doc.build(el)


def cover_output_path(company: str, title: str, cover_dir: Path) -> Path:
    return cover_dir / (
        f"CoverLetter_{safe_filename(company)}_{safe_filename(title)}.pdf"
    )
