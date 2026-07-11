"""Phase 3 - CV generator.

For each 'matched' job: AI tailors the master CV (facts only, reordered and
reworded for the job), then reportlab renders a single-page PDF styled after
the CVs that won education opportunities: big name header, thin rules,
uppercase section titles, right-aligned dates, label -> value skill rows.
Output: output/cvs/CV_<Name>_<Company>.pdf - the master file is never touched.
"""
import re

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

import ai
import config
import db

INK = colors.HexColor("#1b1b1f")
ACCENT = colors.HexColor("#b8860b")
GREY = colors.HexColor("#5a5a63")
LINE = colors.HexColor("#d8d6cf")

S = {
    "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=22,
                           textColor=INK, leading=26, spaceAfter=1.5 * mm),
    "role": ParagraphStyle("role", fontName="Helvetica", fontSize=10.5,
                           textColor=ACCENT, spaceAfter=2 * mm),
    "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=8.5,
                              textColor=GREY, spaceAfter=1 * mm),
    "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=9.5,
                              textColor=INK, spaceBefore=4.5 * mm, spaceAfter=1 * mm),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.3,
                           textColor=INK, leading=13, spaceAfter=1 * mm),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.2,
                             textColor=INK, leading=12.5, leftIndent=4.5 * mm,
                             bulletIndent=1 * mm, spaceAfter=0.7 * mm),
    "job_head": ParagraphStyle("job_head", fontName="Helvetica-Bold", fontSize=10,
                               textColor=INK, spaceBefore=1.6 * mm),
    "date": ParagraphStyle("date", fontName="Helvetica", fontSize=8.8,
                           textColor=GREY, alignment=TA_RIGHT),
    "skill_label": ParagraphStyle("skill_label", fontName="Helvetica-Bold",
                                  fontSize=9, textColor=INK, leading=12.5),
    "skill_value": ParagraphStyle("skill_value", fontName="Helvetica",
                                  fontSize=9, textColor=GREY, leading=12.5),
}


def _safe_filename(text: str) -> str:
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
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _strip_dashes(obj):
    """No em/en dashes anywhere in the CV, ever. Replace recursively."""
    if isinstance(obj, str):
        return obj.replace("\u2014", "-").replace("\u2013", "-")
    if isinstance(obj, list):
        return [_strip_dashes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _strip_dashes(v) for k, v in obj.items()}
    return obj


def _render_pdf(cv: dict, out_path) -> None:
    cv = _strip_dashes(cv)
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=14 * mm, bottomMargin=13 * mm,
    )
    el = []
    c = cv.get("contact", {})

    # ---- Header
    el.append(Paragraph(cv.get("name", "").upper(), S["name"]))
    el.append(Paragraph(cv.get("title", ""), S["role"]))
    contact_bits = [x for x in (c.get("location"), c.get("email"), c.get("phone")) if x]
    links = [x for x in (c.get("linkedin"), c.get("github"), c.get("website")) if x]
    el.append(Paragraph("   |   ".join(contact_bits), S["contact"]))
    if links:
        el.append(Paragraph("   |   ".join(links), S["contact"]))
    el.append(HRFlowable(width="100%", thickness=1.1, color=ACCENT, spaceBefore=1.5 * mm))

    # ---- Objective / summary
    if cv.get("summary"):
        el.extend(_section("Objective"))
        el.append(Paragraph(cv["summary"], S["body"]))

    # ---- Work experience
    if cv.get("experience"):
        el.extend(_section("Work Experience"))
        for exp in cv["experience"]:
            el.append(_head_row(
                f"{exp.get('role', '')} | {exp.get('company', '')}",
                exp.get("period", ""),
            ))
            for b in exp.get("bullets", []):
                el.append(Paragraph(b, S["bullet"], bulletText="•"))

    # ---- Skills (label -> value rows)
    if cv.get("skills"):
        el.extend(_section("Skills"))
        rows = [
            [Paragraph(g.get("category", ""), S["skill_label"]),
             Paragraph(", ".join(g.get("items", [])), S["skill_value"])]
            for g in cv["skills"]
        ]
        t = Table(rows, colWidths=["24%", "76%"])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        el.append(t)

    # ---- Projects
    if cv.get("projects"):
        el.extend(_section("Projects"))
        for p in cv["projects"]:
            tech = ", ".join(p.get("tech", []))
            el.append(Paragraph(f"<b>{p.get('name', '')}</b>", S["body"]))
            el.append(Paragraph(
                f"{p.get('description', '')}"
                + (f" <font color='#5a5a63' size='8'>[{tech}]</font>" if tech else ""),
                S["bullet"],
            ))

    # ---- Education
    if cv.get("education"):
        el.extend(_section("Education"))
        for e in cv["education"]:
            el.append(_head_row(
                f"{e.get('degree', '')} | {e.get('school', '')}",
                e.get("period", "") or "",
            ))
            if e.get("detail"):
                el.append(Paragraph(e["detail"], S["bullet"]))

    # ---- Languages
    if cv.get("languages"):
        el.extend(_section("Languages"))
        el.append(Paragraph(", ".join(cv["languages"]), S["body"]))

    doc.build(el)


def generate_for_matched(log=None) -> int:
    """Generate a tailored CV PDF for every 'matched' job without one. Returns count."""
    emit = log or print
    master = (config.PROFILE_DIR / "master_cv.md").read_text(encoding="utf-8")
    conn = db.connect()
    jobs = [j for j in db.jobs_with_status(conn, "matched") if not j["cv_path"]]
    total = len(jobs)
    done = 0
    emit(f"[CV] {total} matched job(s) need a CV")
    if total == 0:
        conn.close()
        emit("[CV] Nothing to generate")
        return 0

    for i, job in enumerate(jobs, start=1):
        company = (job["company"] or "?").encode("ascii", "replace").decode()
        title = (job["title"] or "?").encode("ascii", "replace").decode()
        emit(f"[CV] {i}/{total}  #{job['id']} {company} — {title}…")
        prompt = ai.load_prompt(
            "tailor_cv",
            master_cv=master,
            company=job["company"] or "unknown",
            title=job["title"] or "unknown",
            skills=job["skills"] or "[]",
            description=job["description"] or "",
        )
        try:
            cv = ai.ask_json(prompt)
            name = _safe_filename(cv.get("name", "CV"))
            company_fn = _safe_filename(job["company"] or f"job{job['id']}")
            out_path = config.OUTPUT_DIR / "cvs" / f"CV_{name}_{company_fn}.pdf"
            _render_pdf(cv, out_path)
        except Exception as e:
            emit(f"[CV] ! failed #{job['id']} ({title}): {e}")
            continue

        db.update_job(conn, job["id"], cv_path=str(out_path))
        emit(f"[CV] {i}/{total} ready · {out_path.name}")
        done += 1

    conn.close()
    emit(f"[CV] Done — {done}/{total} generated")
    return done


if __name__ == "__main__":
    n = generate_for_matched()
    print(f"\nGenerated {n} CV(s).")
