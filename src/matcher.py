"""Phase 2 - Job matcher.

Scores every 'found' job against profile/about_me.md using the AI brain.
Decision buckets (thresholds from .env):
    apply   -> status 'matched'   (queued for CV generation + application)
    review  -> status 'review'    (human looks at it)
    skip    -> status 'skipped'

Also applies a deterministic bump for remote + backend/fullstack so preference
survives even if the model under-weights location/role.
"""
import json
import re

import ai
import config
import db


BATCH_SIZE = 10

REMOTE_BUMP = 12
BACKEND_FULLSTACK_BUMP = 6
IT_SUPPORT_BUMP = 5
REMOTE_RE = re.compile(
    r"\b(remote|work[\s-]?from[\s-]?anywhere|wfh|worldwide|distributed|fully remote)\b",
    re.I,
)
BACKEND_FS_RE = re.compile(
    r"\b(back[\s-]?end|backend|full[\s-]?stack|fullstack|software engineer)\b",
    re.I,
)
IT_SUPPORT_RE = re.compile(
    r"\b(it support|help\s?desk|desktop support|technical support|"
    r"system admin|sysadmin|computer support|tech support)\b",
    re.I,
)
# Years-of-experience that are too senior for ~1yr profile
HEAVY_YEARS_RE = re.compile(
    r"\b([5-9]|[1-9]\d)\+?\s*(?:years?|yrs?)\b|\b(?:senior|lead|principal|staff)\b",
    re.I,
)
SALARY_NUM_RE = re.compile(
    r"(?:etb|br\.?|birr)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,7})\s*(?:etb|br\.?|birr|/mo|/month)?",
    re.I,
)


def _looks_it_support(job, verdict: dict) -> bool:
    role = str(verdict.get("role_fit") or "").lower()
    if role in {"it_support", "support"}:
        return True
    blob = " ".join(str(x or "") for x in (job["title"], job["description"]))
    return bool(IT_SUPPORT_RE.search(blob))


def _salary_number(job) -> int | None:
    """Parse a monthly ETB-ish number if present. None = not listed."""
    blob = " ".join(str(x or "") for x in (job["salary"], job["description"], job["title"]))
    if not blob.strip():
        return None
    # Only treat as "listed" when salary field exists or clear ETB markers appear
    salary_field = (job["salary"] or "").strip()
    if not salary_field and not re.search(r"\b(etb|birr|br\.?)\b", blob, re.I):
        return None
    m = SALARY_NUM_RE.search(salary_field or blob)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _apply_preference_bumps(job, score: int, verdict: dict) -> tuple[int, list[str]]:
    """Deterministic preference bumps on top of the AI score (capped at 100)."""
    reasons = list(verdict.get("reasons") or [])
    bumped = score

    if _looks_remote(job, verdict):
        bumped = min(100, bumped + REMOTE_BUMP)
        reasons.append(f"+{REMOTE_BUMP} remote preference bump")

    if _looks_backend_or_fullstack(job, verdict):
        bumped = min(100, bumped + BACKEND_FULLSTACK_BUMP)
        reasons.append(f"+{BACKEND_FULLSTACK_BUMP} backend/full-stack preference bump")

    if _looks_it_support(job, verdict):
        bumped = min(100, bumped + IT_SUPPORT_BUMP)
        reasons.append(f"+{IT_SUPPORT_BUMP} IT support / CS-degree fit bump")

    # Soft penalty only when experience clearly demands 5+ years / senior+
    exp_blob = " ".join(str(x or "") for x in (job["experience"], job["title"], job["description"]))
    if HEAVY_YEARS_RE.search(exp_blob) and bumped >= config.MATCH_THRESHOLD_APPLY:
        bumped = max(0, bumped - 8)
        reasons.append("-8 heavy years/senior requirement soft penalty")

    # Ethiopia salary floor ONLY when a number is listed
    salary = _salary_number(job)
    loc = " ".join(str(x or "") for x in (job["location"], job["description"])).lower()
    looks_ethiopia = bool(re.search(r"\b(ethiopia|addis|etb|birr)\b", loc)) or bool(
        re.search(r"\b(etb|birr)\b", str(job["salary"] or ""), re.I)
    )
    if salary is not None and looks_ethiopia and salary < 30000:
        bumped = min(bumped, config.MATCH_THRESHOLD_REVIEW - 1)
        reasons.append(f"salary {salary} ETB below 30k floor → force skip band")

    return bumped, reasons


def _profile_text() -> str:
    return (config.PROFILE_DIR / "about_me.md").read_text(encoding="utf-8")


def _job_block(job) -> str:
    return (
        f"=== JOB ID {job['id']} ===\n"
        f"Company: {job['company'] or 'unknown'}\n"
        f"Title: {job['title'] or 'unknown'}\n"
        f"Location: {job['location'] or 'not specified'}\n"
        f"Salary: {job['salary'] or 'not specified'}\n"
        f"Experience required: {job['experience'] or 'not specified'}\n"
        f"Skills: {job['skills'] or '[]'}\n"
        f"Description: {job['description'] or ''}"
    )


def _looks_remote(job, verdict: dict) -> bool:
    if verdict.get("is_remote") is True:
        return True
    blob = " ".join(
        str(x or "")
        for x in (job["location"], job["title"], job["description"])
    )
    return bool(REMOTE_RE.search(blob))


def _looks_backend_or_fullstack(job, verdict: dict) -> bool:
    role = str(verdict.get("role_fit") or "").lower()
    if role in {"backend", "fullstack"}:
        return True
    blob = " ".join(str(x or "") for x in (job["title"], job["description"]))
    return bool(BACKEND_FS_RE.search(blob))


def _decide(score: int, flagged: bool) -> str:
    if flagged or (
        config.MATCH_THRESHOLD_REVIEW <= score < config.MATCH_THRESHOLD_APPLY
    ):
        return "review"
    if score >= config.MATCH_THRESHOLD_APPLY:
        return "matched"
    return "skipped"


def _match_jobs(jobs, log=None) -> dict:
    """Score a list of jobs. Returns counts per decision."""
    emit = log or print
    profile = _profile_text()
    conn = db.connect()
    counts = {"matched": 0, "review": 0, "skipped": 0, "failed": 0}
    total = len(jobs)
    emit(f"[Match] {total} job(s) to score")
    if total == 0:
        conn.close()
        emit("[Match] Nothing to match")
        return counts

    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    done = 0
    for bi, start in enumerate(range(0, total, BATCH_SIZE), start=1):
        batch = jobs[start : start + BATCH_SIZE]
        emit(f"[Match] Batch {bi}/{batches} ({len(batch)} jobs)…")
        blob = "\n\n".join(_job_block(j) for j in batch)
        prompt = ai.load_prompt("match_job", profile=profile, jobs=blob)
        try:
            verdicts = ai.ask_json(prompt)
            verdicts = {int(k): v for k, v in verdicts.items()}
        except Exception as e:
            emit(f"[Match] ! batch {bi} failed: {e}")
            counts["failed"] += len(batch)
            done += len(batch)
            continue

        for job in batch:
            verdict = verdicts.get(job["id"])
            if not isinstance(verdict, dict):
                counts["failed"] += 1
                done += 1
                continue
            raw_score = int(verdict.get("score", 0))
            flagged = bool(verdict.get("flag_for_review"))
            score, reasons = _apply_preference_bumps(job, raw_score, verdict)
            status = _decide(score, flagged)
            counts[status] += 1
            done += 1

            db.update_job(
                conn,
                job["id"],
                status=status,
                match_score=score,
                match_reasons=json.dumps(reasons),
            )
            company = (job["company"] or "?").encode("ascii", "replace").decode()
            title = (job["title"] or "?").encode("ascii", "replace").decode()
            emit(
                f"[Match] {done}/{total}  [{score:3d}] {status:8s} {company} - {title}"
                + (f"  (raw {raw_score})" if score != raw_score else "")
            )

        emit(
            f"[Match] Progress {done}/{total} · "
            f"matched={counts['matched']} review={counts['review']} "
            f"skipped={counts['skipped']} failed={counts['failed']}"
        )

    conn.close()
    emit(f"[Match] Done — {counts}")
    return counts


def match_pending(log=None) -> dict:
    """Match all jobs with status 'found'. Returns counts per decision."""
    conn = db.connect()
    jobs = db.jobs_with_status(conn, "found")
    conn.close()
    return _match_jobs(jobs, log=log)


def rematch_existing() -> dict:
    """Re-score jobs already in the pipeline (found/matched/review/skipped).

    Leaves applied / applying / manual / interview / offer / rejected alone.
    Clears cv_path when a previously matched job drops out of 'matched'
    so stale CVs are not reused.
    """
    conn = db.connect()
    rows = conn.execute(
        """
        SELECT * FROM jobs
        WHERE status IN ('found', 'matched', 'review', 'skipped')
        ORDER BY id
        """
    ).fetchall()
    # Snapshot previous status/cv so we can clear stale CVs after rematch.
    previous = {r["id"]: (r["status"], r["cv_path"]) for r in rows}
    conn.close()

    counts = _match_jobs(rows)

    conn = db.connect()
    for job_id, (old_status, old_cv) in previous.items():
        row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            continue
        if old_status == "matched" and row["status"] != "matched" and old_cv:
            db.update_job(conn, job_id, cv_path=None)
    conn.close()
    return counts


if __name__ == "__main__":
    result = match_pending()
    print(f"\nDone: {result}")
