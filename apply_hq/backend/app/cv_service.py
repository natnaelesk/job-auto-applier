"""CV + cover letter generation for Apply HQ Notion rows."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import config, notion_store, pdf_render
from .ai_brain import AIBrain, AIUnavailableError, get_brain
from .mapping import Board


Emit = Callable[[str], None]


def _read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _job_fields(row: dict) -> tuple[str, str, str, str]:
    company = row.get("company") or row.get("client") or "Company"
    title = row.get("role") or row.get("name") or "Role"
    location = row.get("location") or ""
    description = "\n".join(
        x
        for x in (
            row.get("why") or "",
            row.get("stack") or "",
            row.get("salary") or row.get("budget") or "",
            row.get("notes") or "",
        )
        if x
    )
    return company, title, location, description


def generate_cv_for_row(
    board: Board,
    row: dict,
    *,
    brain: AIBrain | None = None,
    log: Emit | None = None,
) -> Path:
    """Tailor + render CV. Raises AIUnavailableError if brain/profile missing."""
    emit = log or (lambda m: None)
    brain = brain or get_brain()
    ok, reason = brain.available()
    if not ok:
        raise AIUnavailableError(reason)

    master = config.PROFILE_DIR / "master_cv.md"
    if not master.exists():
        raise AIUnavailableError(f"master_cv.md missing at {master}")

    company, title, _loc, description = _job_fields(row)
    emit(f"[CV] Tailoring for {company} — {title}…")

    if not isinstance(brain, type(None)) and hasattr(brain, "load_prompt"):
        prompt = brain.load_prompt(  # type: ignore[attr-defined]
            "tailor_cv",
            master_cv=master.read_text(encoding="utf-8"),
            company=company,
            title=title,
            skills=row.get("stack") or "[]",
            description=description[:4000],
        )
    else:
        raise AIUnavailableError("AI brain cannot load prompts")

    cv = brain.ask_json(prompt)
    name = pdf_render.safe_filename(cv.get("name", "CV"))
    out = pdf_render.cv_output_path(name, company, config.CV_DIR)
    pdf_render.render_cv_pdf(cv, out)
    emit(f"[CV] Saved {out}")

    notion_store.write_cv(board, row["page_id"], str(out))
    emit(f"[CV] Notion updated: CV path + Has CV")
    return out


def build_cvs(
    board: Board,
    *,
    page_id: str | None = None,
    limit: int = 20,
    log: Emit | None = None,
) -> dict:
    """Build CV for Has CV unchecked rows (or one page_id)."""
    emit = log or (lambda m: None)
    brain = get_brain()
    ok, reason = brain.available()
    if not ok:
        emit(f"[CV] ! {reason}")
        return {"ok": False, "reason": reason, "done": 0, "failed": 0, "paths": []}

    if page_id:
        rows = [notion_store.get_page(board, page_id)]
    else:
        rows = notion_store.list_needs_cv(board)[:limit]

    emit(f"[CV] {len(rows)} row(s) need a CV on {board}")
    done = 0
    failed = 0
    paths: list[str] = []
    for row in rows:
        try:
            path = generate_cv_for_row(board, row, brain=brain, log=emit)
            paths.append(str(path))
            done += 1
        except AIUnavailableError as e:
            emit(f"[CV] ! unavailable: {e}")
            return {"ok": False, "reason": str(e), "done": done, "failed": failed + 1, "paths": paths}
        except Exception as e:
            failed += 1
            emit(f"[CV] ! failed {row.get('name')}: {e}")
    return {"ok": True, "reason": "ok", "done": done, "failed": failed, "paths": paths}


def generate_cover_letter(
    board: Board,
    row: dict,
    *,
    user_note: str = "",
    brain: AIBrain | None = None,
    log: Emit | None = None,
) -> Path:
    emit = log or (lambda m: None)
    brain = brain or get_brain()
    ok, reason = brain.available()
    if not ok:
        raise AIUnavailableError(reason)

    profile = ""
    about = config.PROFILE_DIR / "about_me.md"
    answers = config.PROFILE_DIR / "answers.md"
    master = config.PROFILE_DIR / "master_cv.md"
    if about.exists():
        profile += about.read_text(encoding="utf-8") + "\n\n"
    if answers.exists():
        profile += answers.read_text(encoding="utf-8") + "\n\n"
    cv_text = master.read_text(encoding="utf-8") if master.exists() else ""

    company, title, location, description = _job_fields(row)
    emit(f"[Cover] Writing letter for {company} — {title}…")

    if not hasattr(brain, "load_prompt"):
        raise AIUnavailableError("AI brain cannot load prompts")

    prompt = brain.load_prompt(  # type: ignore[attr-defined]
        "cover_letter",
        profile=profile[:6000],
        cv_text=cv_text[:6000],
        company=company,
        title=title,
        location=location,
        description=description[:2500],
        user_note=(user_note or "").strip() or "(none)",
    )
    data = brain.ask_json(prompt)
    if not data.get("paragraphs"):
        raise RuntimeError("AI returned no letter body")

    def scrub(o):
        if isinstance(o, str):
            return o.replace("\u2014", "-").replace("\u2013", "-")
        if isinstance(o, list):
            return [scrub(x) for x in o]
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items()}
        return o

    data = scrub(data)
    out = pdf_render.cover_output_path(company, title, config.COVER_DIR)
    pdf_render.render_cover_pdf(data, out)
    notion_store.write_cover(board, row["page_id"], str(out))
    emit(f"[Cover] Saved {out}")
    return out
