"""Cover letter PDF generator for Apply tab.

Saves to: output/cvs/cover_letter/CoverLetter_<Company>_<Title>.pdf
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import ai
import config

INK = colors.HexColor("#1b1b1f")
GREY = colors.HexColor("#5a5a63")

COVER_DIR = config.OUTPUT_DIR / "cvs" / "cover_letter"


def _safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text or "unknown").strip("_")[:40]


def _styles() -> dict:
    return {
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


def _render_pdf(data: dict, out_path: Path) -> None:
    S = _styles()
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
    el.append(Paragraph(name, S["header"]))
    contact = data.get("contact_line") or ""
    if contact:
        el.append(Paragraph(contact.replace("\n", "<br/>"), S["meta"]))
    el.append(Spacer(1, 4 * mm))
    date = data.get("date") or ""
    if date:
        el.append(Paragraph(date, S["meta"]))
    el.append(Spacer(1, 3 * mm))
    greeting = data.get("greeting") or "Dear Hiring Team,"
    el.append(Paragraph(greeting, S["body"]))
    for para in data.get("paragraphs") or []:
        text = str(para).replace("\n", " ").strip()
        if text:
            el.append(Paragraph(text, S["body"]))
    closing = data.get("closing") or "Sincerely,"
    el.append(Paragraph(closing, S["body"]))
    el.append(Paragraph(name, S["body"]))
    doc.build(el)


def generate_for_job(job, *, user_note: str = "", log=None) -> Path | None:
    """Generate a cover letter PDF for one job. Returns path or None."""
    emit = log or print
    COVER_DIR.mkdir(parents=True, exist_ok=True)

    profile = ""
    about = config.PROFILE_DIR / "about_me.md"
    answers = config.PROFILE_DIR / "answers.md"
    master = config.PROFILE_DIR / "master_cv.md"
    if about.exists():
        profile += about.read_text(encoding="utf-8") + "\n\n"
    if answers.exists():
        profile += answers.read_text(encoding="utf-8") + "\n\n"
    cv_text = master.read_text(encoding="utf-8") if master.exists() else ""

    company = job["company"] or "Company"
    title = job["title"] or "Role"
    emit(f"[Cover] Writing letter for {company} — {title}…")

    prompt = ai.load_prompt(
        "cover_letter",
        profile=profile[:6000],
        cv_text=cv_text[:6000],
        company=company,
        title=title,
        location=job["location"] or "",
        description=(job["description"] or "")[:2500],
        user_note=(user_note or "").strip() or "(none)",
    )
    try:
        data = ai.ask_json(prompt)
    except Exception as e:
        emit(f"[Cover] ! AI failed: {e}")
        return None
    if not isinstance(data, dict) or not data.get("paragraphs"):
        emit("[Cover] ! AI returned no letter body")
        return None

    # Strip em dashes
    def scrub(o):
        if isinstance(o, str):
            return o.replace("\u2014", "-").replace("\u2013", "-")
        if isinstance(o, list):
            return [scrub(x) for x in o]
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items()}
        return o

    data = scrub(data)
    out = COVER_DIR / (
        f"CoverLetter_{_safe_filename(company)}_{_safe_filename(title)}.pdf"
    )
    try:
        _render_pdf(data, out)
    except Exception as e:
        emit(f"[Cover] ! PDF render failed: {e}")
        return None
    emit(f"[Cover] Saved: {out}")
    return out
