"""Phase 5 — human-orchestrated apply session helpers.

Opens job links in your default browser (real Firefox) so you can log into
any account. Screenshots + AI answers; Form Fill needs automation mode.
Status changes (applied / closed / later) are driven by the control panel.
"""
from __future__ import annotations

import json
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import ai
import config
import db
import notion_tracker
from applier.browser import BrowserSession


def _read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _normalize_link(raw: str | None) -> str | None:
    """Turn stored apply targets into an openable http(s) URL."""
    link = (raw or "").strip()
    if not link:
        return None
    if link.startswith(("http://", "https://")):
        return link
    # Telegram @handle or t.me path without scheme
    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    if link.startswith("t.me/"):
        return f"https://{link}"
    if link.startswith("www."):
        return f"https://{link}"
    return None


def _open_system_url(url: str) -> None:
    """Open URL in the OS default browser (works from worker threads on Windows)."""
    import os
    import subprocess
    import sys

    if sys.platform == "win32":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return
        except OSError:
            # Empty title arg after `start` so `&` in URLs is not treated as a title
            subprocess.Popen(
                ["cmd", "/c", "start", "", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return
    if not webbrowser.open(url, new=2):
        raise RuntimeError(f"Could not open browser for {url}")


def load_apply_queue(
    limit: int | None = None,
    market: str | None = None,
) -> list:
    """Jobs ready for human-orchestrated apply (have a CV).

    Keeps unmatched-in-progress work: applying / later / manual stay in the
    queue until Applied or Closed. Applying jobs are listed first so Reload
    resumes them instead of jumping to a new matched job.

    market: None = all, 'ethiopia' | 'foreign' to filter.
    """
    limit = limit if limit is not None else max(config.MAX_APPLY_PER_RUN, 50)
    conn = db.connect()
    if market:
        rows = conn.execute(
            """
            SELECT * FROM jobs
            WHERE cv_path IS NOT NULL AND cv_path != ''
              AND status IN ('matched', 'later', 'manual', 'applying', 'failed')
              AND COALESCE(market, 'ethiopia') = ?
            ORDER BY
              CASE status
                WHEN 'applying' THEN 0
                WHEN 'matched' THEN 1
                WHEN 'later' THEN 2
                WHEN 'manual' THEN 3
                ELSE 4
              END,
              match_score DESC,
              id ASC
            LIMIT ?
            """,
            (market, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM jobs
            WHERE cv_path IS NOT NULL AND cv_path != ''
              AND status IN ('matched', 'later', 'manual', 'applying', 'failed')
            ORDER BY
              CASE status
                WHEN 'applying' THEN 0
                WHEN 'matched' THEN 1
                WHEN 'later' THEN 2
                WHEN 'manual' THEN 3
                ELSE 4
              END,
              match_score DESC,
              id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return list(rows)


def job_shot_dir(job_id: int) -> Path:
    d = config.OUTPUT_DIR / "screenshots" / f"job_{job_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ApplySession:
    """Apply tab session — default OS browser by default (not automation)."""

    def __init__(self, log=None):
        self.log = log or (lambda m: None)
        self.browser = BrowserSession(log=self.log)
        self.jobs: list = []
        self.index = 0
        self.shots: list[Path] = []
        self.answers: list[dict] = []
        self.profile = _read(config.PROFILE_DIR / "about_me.md")
        self.answers_bank = _read(config.PROFILE_DIR / "answers.md")
        self._started = False
        self.system_browser = bool(getattr(config, "APPLY_SYSTEM_BROWSER", True))
        self.market_filter: str | None = None  # None | ethiopia | foreign

    @property
    def job(self):
        if 0 <= self.index < len(self.jobs):
            return self.jobs[self.index]
        return None

    def start(self, jobs: list | None = None, resume_id: int | None = None) -> None:
        keep_id = resume_id
        if keep_id is None and self.job is not None:
            keep_id = int(self.job["id"])

        self.jobs = (
            jobs
            if jobs is not None
            else load_apply_queue(market=self.market_filter)
        )
        self.index = 0
        resumed = False
        if keep_id is not None:
            for i, j in enumerate(self.jobs):
                if int(j["id"]) == int(keep_id):
                    self.index = i
                    resumed = True
                    break

        if not resumed:
            self.shots = []
            self.answers = []
            for i, j in enumerate(self.jobs):
                if j["status"] == "applying":
                    self.index = i
                    break

        if self.system_browser:
            self.log(
                "Links open in your default browser (real Firefox) — "
                "log into any account you need."
            )
            self.log(
                "Workflow: Open Link → Region Shot → add question → Analyze → "
                "Copy answers → Applied/Closed/Later."
            )
        elif not self._started:
            self.browser.start()
            self._started = True

        if self.job:
            if resumed:
                self.log(
                    f"Resumed #{self.job['id']} {self.job['company']} — "
                    f"{self.job['title']} (still in queue until Applied/Closed)"
                )
            else:
                self.log(
                    f"Current #{self.job['id']} {self.job['company']} — "
                    f"{self.job['title']}"
                )
        self.log(f"Apply queue: {len(self.jobs)} job(s)")

    def stop(self) -> None:
        if self._started:
            self.browser.stop()
            self._started = False

    def open_current(self) -> bool:
        job = self.job
        if not job:
            self.log("No job in queue — click Start / Reload first")
            return False

        # Skip jobs with no openable link
        skipped = 0
        while self.job is not None:
            job = self.job
            link = _normalize_link(job["link"])
            if link:
                break
            self.log(
                f"Skip #{job['id']} — no openable link "
                f"({(job['link'] or job['apply_method'] or 'empty')!r})"
            )
            skipped += 1
            if self.index + 1 >= len(self.jobs):
                self.log("No jobs left with an openable http link")
                return False
            self.index += 1
            self.shots = []
            self.answers = []

        job = self.job
        assert job and link

        conn = db.connect()
        db.update_job(conn, job["id"], status="applying", block_reason=None)
        conn.close()
        self.shots = []
        self.answers = []
        try:
            if self.system_browser:
                _open_system_url(link)
                self.log(
                    f"Opened in default browser #{job['id']} "
                    f"{job['company']} — {job['title']}"
                )
                self.log(f"URL: {link}")
            else:
                if not self._started:
                    self.browser.start()
                    self._started = True
                self.browser.goto(link, wait_ms=1200)
                self.log(f"Opened #{job['id']} {job['company']} — {job['title']}")
        except Exception as e:
            self.log(f"Open failed: {e}")
            return False
        if skipped:
            self.log(f"(skipped {skipped} job(s) without links)")
        return True

    def next_job(self) -> bool:
        """Move to next job. Current stays in queue unless Applied/Closed."""
        cur = self.job
        if cur and cur["status"] == "applying":
            # Park as later so it is not lost and Reload can still find it
            conn = db.connect()
            db.update_job(conn, cur["id"], status="later")
            conn.close()
            self.log(
                f"Parked #{cur['id']} as later (not Applied/Closed — still in queue)"
            )

        if self.index + 1 >= len(self.jobs):
            self.jobs = load_apply_queue(market=self.market_filter)
            self.index = 0
            self.shots = []
            self.answers = []
            if not self.jobs:
                self.log("End of queue")
                return False
            return self.open_current()

        self.index += 1
        self.shots = []
        self.answers = []
        return self.open_current()

    def _next_shot_path(self, tag: str) -> Path:
        job = self.job
        assert job
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        return job_shot_dir(job["id"]) / f"{tag}_{ts}.png"

    def _grab_screen(self, path: Path) -> Path:
        from PIL import ImageGrab

        img = ImageGrab.grab(all_screens=True)
        img.save(path)
        return path

    def screenshot_page(self) -> Path | None:
        if not self.job:
            return None
        path = self._next_shot_path("page")
        try:
            if self.system_browser or not self.browser.page:
                self._grab_screen(path)
                self.shots.append(path)
                self.log(
                    f"Screen captured: {path.name} "
                    "(prefer Region Shot to crop just the form)"
                )
                return path
            self.browser.screenshot(path)
            self.shots.append(path)
            self.log(f"Screenshot saved: {path.name}")
            return path
        except Exception as e:
            self.log(f"Screenshot failed: {e}")
            return None

    def screenshot_scroll(self) -> Path | None:
        """Scroll in automation browser, or remind user then capture screen."""
        if self.system_browser or not self.browser.page:
            self.log("Scroll in Firefox yourself, then Page Shot / Region Shot.")
            return self.screenshot_page()
        try:
            self.browser.page.evaluate(
                "window.scrollBy(0, Math.floor(window.innerHeight * 0.85))"
            )
            self.browser.page.wait_for_timeout(400)
        except Exception as e:
            self.log(f"Scroll failed: {e}")
        return self.screenshot_page()

    def analyze_form(self, user_note: str = "") -> list[dict]:
        job = self.job
        if not job:
            return []
        if not self.shots:
            self.screenshot_page()
        if not self.shots:
            self.log("No screenshots to analyze")
            return []

        cv_text = ""
        if job["cv_path"]:
            cv_text = _read(config.PROFILE_DIR / "master_cv.md")

        note = (user_note or "").strip() or (
            "(none — trust screenshots; if they do not match the JOB block, "
            "say so in notes and answer the form in the screenshots)"
        )
        prompt = ai.load_prompt(
            "read_form_screenshots",
            profile=self.profile,
            answers=self.answers_bank,
            cv_text=cv_text[:8000],
            company=job["company"] or "",
            title=job["title"] or "",
            location=job["location"] or "",
            description=(job["description"] or "")[:2500],
            user_note=note,
        )
        self.log(f"Analyzing {len(self.shots)} screenshot(s) with AI…")
        if (user_note or "").strip():
            self.log(f"Your note: {(user_note or '').strip()[:160]}")
        try:
            data = ai.ask_json_with_images(prompt, self.shots)
        except Exception as e:
            self.log(f"Analyze failed: {e}")
            return []

        fields = data.get("fields") if isinstance(data, dict) else None
        if not isinstance(fields, list):
            self.log("AI returned no fields")
            return []
        self.answers = [
            {
                "label": str(f.get("label") or ""),
                "answer": str(f.get("answer") or ""),
                "field_type": str(f.get("field_type") or "text"),
                "confidence": str(f.get("confidence") or "medium"),
            }
            for f in fields
            if isinstance(f, dict)
        ]
        tip = (data.get("notes") or "") if isinstance(data, dict) else ""
        if tip:
            self.log(f"AI tip: {tip}")
        self.log(f"Got {len(self.answers)} field answer(s)")

        conn = db.connect()
        db.update_job(
            conn,
            job["id"],
            apply_answers=json.dumps(self.answers),
            screenshot_path=str(self.shots[-1]) if self.shots else None,
        )
        conn.close()
        return self.answers

    def generate_cover_letter(self, user_note: str = "") -> Path | None:
        """Create a cover letter PDF under output/cvs/cover_letter/."""
        import cover_letter

        job = self.job
        if not job:
            self.log("No job loaded — Start / Reload first")
            return None
        path = cover_letter.generate_for_job(job, user_note=user_note, log=self.log)
        if path:
            self.log(f"Upload this for Cover Letter: {path.name}")
            self.log(f"Folder: {path.parent}")
        return path

    def form_fill(self) -> bool:
        """Auto-fill the open page using DOM snapshot + known answers."""
        job = self.job
        if self.system_browser or not self.browser.page:
            self.log(
                "Form Fill needs automation browser. "
                "With default Firefox: copy answers from the list and paste yourself. "
                "Or set APPLY_SYSTEM_BROWSER=false in .env for auto-fill."
            )
            return False
        if not job:
            return False
        form = self.browser.form_snapshot()
        files: dict[str, Path] = {}
        if job["cv_path"]:
            files["cv"] = Path(job["cv_path"])
        if config.DEGREE_PDF.exists():
            files["degree"] = config.DEGREE_PDF
        if config.GRADES_PDF.exists():
            files["grades"] = config.GRADES_PDF
        if config.ENGLISH_MEDIUM_PDF.exists():
            files["english_medium"] = config.ENGLISH_MEDIUM_PDF

        answers_hint = json.dumps(self.answers, ensure_ascii=False)[:4000]
        prompt = ai.load_prompt(
            "fill_form",
            profile=self.profile,
            answers=self.answers_bank + "\n\nPRECOMPUTED FIELD ANSWERS:\n" + answers_hint,
            passport=_read(config.PASSPORT_DATA),
            cv_path=str(files.get("cv", "")),
            degree_path=str(files.get("degree", "")),
            grades_path=str(files.get("grades", "")),
            english_path=str(files.get("english_medium", "")),
            company=job["company"] or "",
            title=job["title"] or "",
            location=job["location"] or "",
            description=(job["description"] or "")[:2500],
            form=form,
        )
        self.log("Building Form Fill plan…")
        try:
            plan = ai.ask_json(prompt)
        except Exception as e:
            self.log(f"Form Fill plan failed: {e}")
            return False
        if not isinstance(plan, dict) or plan.get("blocked"):
            self.log(f"Form Fill blocked: {plan.get('block_reason') if isinstance(plan, dict) else plan}")
            return False
        try:
            self.browser.run_actions(plan.get("actions") or [], files)
            self.log("Form Fill actions done (submit left to you)")
            return True
        except Exception as e:
            self.log(f"Form Fill failed: {e}")
            return False

    def set_status(self, status: str, notes: str = "") -> None:
        job = self.job
        if not job:
            return
        fields: dict = {"status": status, "notes": notes}
        if status == "applied":
            fields["applied_at"] = datetime.now(timezone.utc).isoformat()
            fields["block_reason"] = None
        if self.answers:
            fields["apply_answers"] = json.dumps(self.answers)
        if self.shots:
            fields["screenshot_path"] = str(self.shots[-1])

        conn = db.connect()
        db.update_job(conn, job["id"], **fields)
        conn.close()
        self.log(f"Marked #{job['id']} → {status}")
        try:
            ok = notion_tracker.sync_one_job(job["id"])
            self.log("Notion synced" if ok else "Notion sync failed")
        except Exception as e:
            self.log(f"Notion sync error: {e}")


def run_scan(log=None) -> int:
    import asyncio
    import telegram_watcher

    log = log or print
    log("[Scan] Starting…")
    n = asyncio.run(telegram_watcher.scan_channel(log=log))
    log("[Scan] Resolving source links…")
    enriched = asyncio.run(telegram_watcher.resolve_source_links(log=log))
    log(f"[Scan] Summary: {n} new, {enriched} enriched")
    return n


def run_extract_match(log=None) -> dict:
    import extractor
    import matcher

    log = log or print
    log("[Extract] Starting…")
    processed, found = extractor.extract_pending(log=log)
    log(f"[Extract] Summary: {processed} msgs → {found} jobs")
    log("[Match] Starting…")
    counts = matcher.match_pending(log=log)
    log(f"[Match] Summary: {counts}")
    return counts


def run_cv_notion(log=None) -> tuple[int, int, int]:
    from services.notion_cv_service import NotionCVService

    log = log or print
    result = NotionCVService(log=log).generate_and_sync()
    cvs = int(result.get("cvs") or 0)
    eth = result.get("ethiopia") or {}
    foreign = result.get("foreign") or {}
    c = int(eth.get("created") or 0) + int(foreign.get("created") or 0)
    u = int(eth.get("updated") or 0) + int(foreign.get("updated") or 0)
    return cvs, c, u


def run_gather_pipeline(log=None) -> None:
    """Phases 1–4 + Notion sync (for Gather tab / Run All)."""
    log = log or print
    run_scan(log=log)
    run_extract_match(log=log)
    run_cv_notion(log=log)


def run_gmail_pipeline(log=None) -> None:
    from services.email_service import EmailService
    from services.notion_cv_service import NotionCVService

    log = log or print
    EmailService(log=log).scan()
    log("[Notion] Syncing dirty jobs after Gmail…")
    NotionCVService(log=log).sync_notion()


def run_foreign_search(log=None) -> dict:
    from services.search_service import SearchService
    from services.notion_cv_service import NotionCVService

    log = log or print
    result = SearchService(log=log).search_foreign(match=True)
    NotionCVService(log=log).generate_and_sync()
    return result


def run_all_pipeline(log=None) -> None:
    """Full auto pipeline except human Apply tab."""
    log = log or print
    run_gather_pipeline(log=log)
    run_gmail_pipeline(log=log)
