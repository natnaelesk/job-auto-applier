"""CV + cover letter PDF renderers for Apply HQ.

CV layout: clean ATS Times style (job-pipeline writer), not the old
gold/Helvetica shop look.

Filename: output/cvs/NatnaelEskinder_{Company}_{Title}.pdf
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

# ATS palette — navy/gray only (no gold)
INK = colors.HexColor("#111111")
NAVY = colors.HexColor("#1a1a2e")
BODY = colors.HexColor("#333333")
MUTED = colors.HexColor("#555555")
RULE = colors.HexColor("#cccccc")

# Cover letter keeps a simple dark palette (unchanged intent)
_CL_INK = colors.HexColor("#1b1b1f")
_CL_GREY = colors.HexColor("#5a5a63")


def _cv_styles() -> dict[str, ParagraphStyle]:
    return {
        "name": ParagraphStyle(
            "ats_name",
            fontName="Times-Bold",
            fontSize=16,
            textColor=INK,
            alignment=TA_CENTER,
            leading=18,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "ats_title",
            fontName="Times-Roman",
            fontSize=11,
            textColor=BODY,
            alignment=TA_CENTER,
            leading=13,
            spaceAfter=3,
        ),
        "contact": ParagraphStyle(
            "ats_contact",
            fontName="Times-Roman",
            fontSize=9,
            textColor=MUTED,
            alignment=TA_CENTER,
            leading=11,
            spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "ats_section",
            fontName="Times-Bold",
            fontSize=10.5,
            textColor=NAVY,
            alignment=TA_LEFT,
            leading=12,
            spaceBefore=8,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "ats_body",
            fontName="Times-Roman",
            fontSize=9.5,
            textColor=BODY,
            alignment=TA_LEFT,
            leading=12,
            spaceAfter=3,
        ),
        "job_role": ParagraphStyle(
            "ats_job_role",
            fontName="Times-Bold",
            fontSize=10,
            textColor=INK,
            alignment=TA_LEFT,
            leading=12,
            spaceBefore=4,
            spaceAfter=0,
        ),
        "job_meta": ParagraphStyle(
            "ats_job_meta",
            fontName="Times-Italic",
            fontSize=9,
            textColor=MUTED,
            alignment=TA_LEFT,
            leading=11,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "ats_bullet",
            fontName="Times-Roman",
            fontSize=9.5,
            textColor=BODY,
            alignment=TA_LEFT,
            leading=11.5,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=1,
        ),
        "skill_line": ParagraphStyle(
            "ats_skill_line",
            fontName="Times-Roman",
            fontSize=9.5,
            textColor=BODY,
            alignment=TA_LEFT,
            leading=12,
            spaceAfter=1,
        ),
        "skill_cat": ParagraphStyle(
            "ats_skill_cat",
            fontName="Times-Bold",
            fontSize=9.5,
            textColor=INK,
            alignment=TA_LEFT,
            leading=12,
            spaceAfter=1,
        ),
    }


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text or "unknown").strip("_")[:40]


def ats_name_stem(full_name: str) -> str:
    """'Natnael Eskinder Mengistu' -> 'NatnaelEskinder'."""
    parts = re.findall(r"[A-Za-z]+", full_name or "")
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    if parts:
        return parts[0]
    return "NatnaelEskinder"


def _strip_dashes(obj):
    if isinstance(obj, str):
        return obj.replace("\u2014", "-").replace("\u2013", "-")
    if isinstance(obj, list):
        return [_strip_dashes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _strip_dashes(v) for k, v in obj.items()}
    return obj


def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _section_block(title: str, styles: dict) -> list:
    """Uppercase section header + thin gray rule (never gold)."""
    return [
        Paragraph(title.upper(), styles["section"]),
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=RULE,
            spaceBefore=0,
            spaceAfter=4,
        ),
    ]


def render_cv_pdf(cv: dict, out_path: Path) -> None:
    """Render tailored CV dict as a clean Times/ATS single-page PDF."""
    cv = _strip_dashes(cv)
    styles = _cv_styles()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # US Letter, tight margins (~0.5\")
    margin = 0.5 * inch
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    el: list = []
    c = cv.get("contact") or {}

    # ---- Centered header
    el.append(Paragraph(_esc(cv.get("name", "")).upper(), styles["name"]))
    if cv.get("title"):
        el.append(Paragraph(_esc(cv["title"]), styles["title"]))
    contact_bits = [
        x
        for x in (
            c.get("location"),
            c.get("email"),
            c.get("phone"),
            c.get("linkedin"),
            c.get("github"),
            c.get("website"),
        )
        if x
    ]
    if contact_bits:
        el.append(
            Paragraph("  |  ".join(_esc(x) for x in contact_bits), styles["contact"])
        )

    # ---- SUMMARY
    if cv.get("summary"):
        el.extend(_section_block("SUMMARY", styles))
        el.append(Paragraph(_esc(cv["summary"]), styles["body"]))

    # ---- SKILLS (category lines — not a gold table)
    skills = cv.get("skills") or []
    languages = cv.get("languages") or []
    if skills or languages:
        el.extend(_section_block("SKILLS", styles))
        for g in skills:
            if not isinstance(g, dict):
                continue
            cat = (g.get("category") or "").strip()
            items = g.get("items") or []
            if isinstance(items, list):
                items_s = ", ".join(str(i) for i in items if i)
            else:
                items_s = str(items)
            if not cat and not items_s:
                continue
            if cat:
                el.append(
                    Paragraph(
                        f"<b>{_esc(cat)}:</b> {_esc(items_s)}",
                        styles["skill_line"],
                    )
                )
            else:
                el.append(Paragraph(_esc(items_s), styles["skill_line"]))
        if languages:
            lang_s = ", ".join(str(x) for x in languages if x)
            if lang_s:
                el.append(
                    Paragraph(
                        f"<b>Languages:</b> {_esc(lang_s)}",
                        styles["skill_line"],
                    )
                )

    # ---- EXPERIENCE
    if cv.get("experience"):
        el.extend(_section_block("EXPERIENCE", styles))
        for exp in cv["experience"]:
            role = exp.get("role") or ""
            company = exp.get("company") or ""
            period = exp.get("period") or ""
            location = exp.get("location") or ""
            el.append(Paragraph(_esc(role), styles["job_role"]))
            meta_parts = [x for x in (company, location, period) if x]
            if meta_parts:
                el.append(
                    Paragraph(_esc(" | ".join(meta_parts)), styles["job_meta"])
                )
            for b in exp.get("bullets") or []:
                text = str(b).strip()
                if text:
                    el.append(
                        Paragraph(_esc(text), styles["bullet"], bulletText="•")
                    )

    # ---- PROJECTS
    if cv.get("projects"):
        el.extend(_section_block("PROJECTS", styles))
        for p in cv["projects"]:
            name = p.get("name") or ""
            tech = p.get("tech") or []
            tech_s = ", ".join(str(t) for t in tech if t) if isinstance(tech, list) else str(tech)
            head = _esc(name)
            if tech_s:
                head = f"{head} — {_esc(tech_s)}"
            el.append(Paragraph(f"<b>{head}</b>", styles["job_role"]))
            desc = (p.get("description") or "").strip()
            if desc:
                el.append(Paragraph(_esc(desc), styles["body"]))

    # ---- EDUCATION
    if cv.get("education"):
        el.extend(_section_block("EDUCATION", styles))
        for e in cv["education"]:
            degree = e.get("degree") or ""
            school = e.get("school") or ""
            period = e.get("period") or ""
            el.append(Paragraph(_esc(degree), styles["job_role"]))
            meta_parts = [x for x in (school, period) if x]
            if meta_parts:
                el.append(
                    Paragraph(_esc(" | ".join(meta_parts)), styles["job_meta"])
                )
            if e.get("detail"):
                el.append(Paragraph(_esc(str(e["detail"])), styles["body"]))

    # ---- CERTIFICATES (only if present — never invent)
    certs = cv.get("certificates") or cv.get("certifications") or []
    if certs:
        el.extend(_section_block("CERTIFICATES", styles))
        for cert in certs:
            if isinstance(cert, dict):
                label = cert.get("name") or cert.get("title") or ""
                detail = cert.get("detail") or cert.get("issuer") or cert.get("period") or ""
                line = _esc(label)
                if detail:
                    line = f"{line} — {_esc(str(detail))}"
                if line:
                    el.append(Paragraph(line, styles["body"]))
            else:
                text = str(cert).strip()
                if text:
                    el.append(Paragraph(_esc(text), styles["body"]))

    doc.build(el)


def cv_output_path(
    company: str,
    title: str,
    cv_dir: Path,
    *,
    full_name: str = "Natnael Eskinder Mengistu",
) -> Path:
    """output/cvs/NatnaelEskinder_{Company}_{Title}.pdf"""
    stem = ats_name_stem(full_name)
    return (
        cv_dir
        / f"{safe_filename(stem)}_{safe_filename(company)}_{safe_filename(title)}.pdf"
    )


# --- Cover letter PDF (unchanged simple layout) ---

_CL = {
    "header": ParagraphStyle(
        "cl_header",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=_CL_INK,
        spaceAfter=2,
    ),
    "meta": ParagraphStyle(
        "cl_meta",
        fontName="Helvetica",
        fontSize=9,
        textColor=_CL_GREY,
        leading=12,
        spaceAfter=1,
    ),
    "body": ParagraphStyle(
        "cl_body",
        fontName="Helvetica",
        fontSize=10.5,
        textColor=_CL_INK,
        leading=15,
        spaceAfter=8,
    ),
}


def render_cover_pdf(data: dict, out_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

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
