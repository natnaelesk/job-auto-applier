"""Phase 4 - Notion tracker.

SQLite is the source of truth. Notion is a push mirror.

Two databases:
  - Job Applications Tracker  → market=ethiopia (NOTION_DATABASE_ID)
  - Foreign Jobs Hunt         → market=foreign  (NOTION_FOREIGN_DATABASE_ID)

Default sync is incremental: only rows with notion_dirty=1 are pushed.
Skipped jobs without a Notion page are not created (noise). Use full=True
(or `python src/main.py notion-full`) for a rare repair rewrite.
"""
import json
from pathlib import Path

from notion_client import Client

import config
import db

# Pin a stable API version (classic database endpoints)
NOTION_VERSION = "2022-06-28"

DB_TITLE = "Job Applications Tracker"
FOREIGN_DB_TITLE = "Foreign Jobs Hunt"

# Process-local: schema ensure columns only once per run / per database
_schema_ready: set[str] = set()

# db status -> (Notion label, pill color)
STATUS_META = {
    "found":    ("🔵 Found", "blue"),
    "matched":  ("🟢 Matched", "green"),
    "review":   ("🟠 Needs Review", "orange"),
    "skipped":  ("⚪ Skipped", "gray"),
    "applying": ("🟡 Applying", "yellow"),
    "applied":  ("✅ Applied", "green"),
    "manual":   ("🖐 Manual Apply Needed", "orange"),
    "failed":   ("❌ Failed", "red"),
    "later":    ("⏸ Later", "yellow"),
    "closed":   ("⬛ Closed", "gray"),
    "interview": ("🟣 Interview", "purple"),
    "offer":    ("🏆 Offer", "pink"),
    "rejected": ("🔴 Rejected", "red"),
}

DB_PROPERTIES = {
    "#": {"number": {"format": "number"}},
    "Company": {"title": {}},
    "Role": {"rich_text": {}},
    "Status": {"select": {"options": [
        {"name": label, "color": color} for label, color in STATUS_META.values()
    ]}},
    "Match Score": {"number": {"format": "percent"}},
    # rich_text, not multi_select: AI reasons are sentences (commas break tags)
    "Match Reasons": {"rich_text": {}},
    "Link": {"url": {}},
    "Location": {"rich_text": {}},
    "Salary": {"rich_text": {}},
    "CV Used": {"rich_text": {}},
    "Applied Date": {"date": {}},
    "Notes": {"rich_text": {}},
    "Last Response": {"date": {}},
    "Response Summary": {"rich_text": {}},
    "Source": {"rich_text": {}},
}


def _client() -> Client:
    token = config.require("NOTION_TOKEN", config.NOTION_TOKEN)
    return Client(auth=token, notion_version=NOTION_VERSION)


def _save_env_key(key: str, value: str) -> None:
    """Persist a key into .env and update config module attribute if present."""
    env_path = config.PROJECT_ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if hasattr(config, key):
        setattr(config, key, value)


def _save_database_id(database_id: str, *, market: str = "ethiopia") -> None:
    if market == "foreign":
        _save_env_key("NOTION_FOREIGN_DATABASE_ID", database_id)
    else:
        _save_env_key("NOTION_DATABASE_ID", database_id)


def ensure_database(notion: Client, *, market: str = "ethiopia") -> str:
    """Return the tracker database id for the given market, creating if needed."""
    global _schema_ready

    if market == "foreign":
        existing = config.NOTION_FOREIGN_DATABASE_ID
        title = FOREIGN_DB_TITLE
        emoji = "🌍"
    else:
        existing = config.NOTION_DATABASE_ID
        title = DB_TITLE
        emoji = "🎯"

    if existing:
        if existing not in _schema_ready:
            _ensure_schema_columns(notion, existing)
            _schema_ready.add(existing)
        return existing

    # Find a page the integration was connected to - that's the parent.
    results = notion.search(
        filter={"property": "object", "value": "page"}
    ).get("results", [])
    if not results:
        raise SystemExit(
            "No Notion page is shared with the integration.\n"
            "In Notion: create/open a page -> ... menu -> Connections -> "
            "add 'Job Auto Applier', then rerun."
        )
    parent_id = results[0]["id"]

    # notion-client 3.x strips 'properties' from databases.create (it targets
    # the newer data-source API), so send the raw request for the pinned
    # 2022-06-28 API version instead.
    created = notion.request(
        path="databases",
        method="POST",
        body={
            "parent": {"type": "page_id", "page_id": parent_id},
            "icon": {"type": "emoji", "emoji": emoji},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": DB_PROPERTIES,
        },
    )
    _save_database_id(created["id"], market=market)
    _schema_ready.add(created["id"])
    print(f"  Created Notion database '{title}' (id saved to .env)")
    return created["id"]


def _ensure_schema_columns(notion: Client, database_id: str) -> None:
    """One GET: add missing columns if needed."""
    try:
        db_obj = notion.request(path=f"databases/{database_id}", method="GET")
    except Exception as e:
        print(f"  ! could not read Notion database schema: {e}")
        return

    props = db_obj.get("properties") or {}
    patch: dict = {}
    if "#" not in props:
        patch["#"] = {"number": {"format": "number"}}
    if "Notes" not in props:
        patch["Notes"] = {"rich_text": {}}
    if "Source" not in props:
        patch["Source"] = {"rich_text": {}}
    if not patch:
        return
    try:
        notion.request(
            path=f"databases/{database_id}",
            method="PATCH",
            body={"properties": patch},
        )
        print(f"  Added Notion column(s): {', '.join(patch)}")
    except Exception as e:
        print(f"  ! could not patch Notion schema: {e}")


def _rt(text) -> dict:
    return {"rich_text": [{"text": {"content": str(text)[:2000]}}]} if text else {"rich_text": []}


def _job_properties(job) -> dict:
    label, _ = STATUS_META.get(job["status"], STATUS_META["found"])
    reasons = json.loads(job["match_reasons"]) if job["match_reasons"] else []
    keys = job.keys() if hasattr(job, "keys") else []
    source = None
    if "source" in keys and job["source"]:
        source = job["source"]
    props = {
        "#": {"number": job["id"]},
        "Company": {"title": [{"text": {"content": job["company"] or "Unknown"}}]},
        "Role": _rt(job["title"]),
        "Status": {"select": {"name": label}},
        "Match Reasons": _rt("\n".join(f"• {r}" for r in reasons) if reasons else None),
        "Location": _rt(job["location"]),
        "Salary": _rt(job["salary"]),
        "CV Used": _rt(Path(job["cv_path"]).name if job["cv_path"] else None),
        "Source": _rt(source),
    }
    if job["match_score"] is not None:
        props["Match Score"] = {"number": job["match_score"] / 100}
    if job["link"]:
        props["Link"] = {"url": job["link"]}
    if job["applied_at"]:
        props["Applied Date"] = {"date": {"start": job["applied_at"][:10]}}
    if "notes" in keys and job["notes"]:
        props["Notes"] = _rt(job["notes"])
    if "block_reason" in keys and job["block_reason"]:
        # fold into Match Reasons so we don't need a new Notion property
        extra = f"Block: {job['block_reason']}"
        existing = props["Match Reasons"]["rich_text"]
        if existing:
            existing[0]["text"]["content"] = (
                existing[0]["text"]["content"] + "\n" + extra
            )[:2000]
        else:
            props["Match Reasons"] = _rt(extra)
    if "response_summary" in keys and job["response_summary"]:
        props["Response Summary"] = _rt(job["response_summary"])
    if "last_response_at" in keys and job["last_response_at"]:
        props["Last Response"] = {
            "date": {"start": str(job["last_response_at"])[:10]}
        }
    return props


def _has_page(job) -> bool:
    return bool(job["notion_page_id"])


def _should_create_page(job) -> bool:
    """Do not create Notion pages for skipped noise."""
    return job["status"] != "skipped"


def _job_market(job) -> str:
    keys = job.keys() if hasattr(job, "keys") else []
    if "market" in keys and job["market"]:
        return str(job["market"])
    return "ethiopia"


def _mark_synced(conn, job_id: int, notion_page_id: str | None = None) -> None:
    fields: dict = {"notion_dirty": 0}
    if notion_page_id is not None:
        fields["notion_page_id"] = notion_page_id
    db.update_job(conn, job_id, **fields)


def _push_job(notion: Client, database_id: str, conn, job) -> str:
    """Create or update one Notion page. Returns 'created' | 'updated' | 'skipped'."""
    # Skipped + never mirrored: clear dirty without creating a page.
    if not _has_page(job) and not _should_create_page(job):
        _mark_synced(conn, job["id"])
        return "skipped"

    props = _job_properties(job)
    if _has_page(job):
        notion.pages.update(page_id=job["notion_page_id"], properties=props)
        _mark_synced(conn, job["id"])
        return "updated"

    page = notion.pages.create(
        parent={"database_id": database_id}, properties=props
    )
    _mark_synced(conn, job["id"], notion_page_id=page["id"])
    return "created"


def sync_one_job(job_id: int) -> bool:
    """Push a single job to the Notion DB for its market. Returns True on success."""
    notion = _client()
    conn = db.connect()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        return False
    market = _job_market(job)
    try:
        database_id = ensure_database(notion, market=market)
        action = _push_job(notion, database_id, conn, job)
        conn.close()
        return action in {"created", "updated", "skipped"}
    except Exception as e:
        print(f"  ! Notion sync failed for job {job_id}: {e}")
        conn.close()
        return False


def sync_jobs(
    log=None, *, full: bool = False, market: str | None = None
) -> tuple[int, int]:
    """Push dirty jobs (default) or every job (full=True) to Notion.

    If market is set ('ethiopia' | 'foreign'), only that DB is synced.
    If market is None, syncs both markets separately.

    Returns (created, updated). Skipped-without-page clears dirty locally and
    does not count as created/updated.
    """
    emit = log or print
    if market is None:
        c1, u1 = sync_jobs(log=emit, full=full, market="ethiopia")
        c2, u2 = sync_jobs(log=emit, full=full, market="foreign")
        return c1 + c2, u1 + u2

    mode = "full" if full else "incremental"
    label = "Foreign Jobs Hunt" if market == "foreign" else "Ethiopia Tracker"
    emit(f"[Notion] Connecting {label} ({mode})…")
    notion = _client()
    database_id = ensure_database(notion, market=market)

    conn = db.connect()
    jobs = db.jobs_needing_notion_sync(conn, full=full, market=market)
    total = len(jobs)
    created = updated = failed = skipped_local = 0
    emit(f"[Notion] Syncing {total} {market} job(s)…")
    if total == 0:
        conn.close()
        emit(f"[Notion] Nothing to sync ({market})")
        return 0, 0

    for i, job in enumerate(jobs, start=1):
        title = (job["title"] or "?").encode("ascii", "replace").decode()
        try:
            action = _push_job(notion, database_id, conn, job)
            if action == "created":
                created += 1
            elif action == "updated":
                updated += 1
            else:
                skipped_local += 1
            if i % 10 == 0 or i == total:
                emit(
                    f"[Notion] {i}/{total} · {action} #{job['id']} · "
                    f"created={created} updated={updated}"
                    + (f" skipped={skipped_local}" if skipped_local else "")
                )
        except Exception as e:
            failed += 1
            emit(f"[Notion] ! {i}/{total} failed #{job['id']} ({title}): {e}")

    conn.close()
    emit(
        f"[Notion] Done ({market}) — {created} created, {updated} updated"
        + (f", {skipped_local} skipped-local" if skipped_local else "")
        + (f", {failed} failed" if failed else "")
    )
    return created, updated


if __name__ == "__main__":
    import sys

    full = "--full" in sys.argv
    c, u = sync_jobs(full=full)
    print(f"\nNotion: {c} page(s) created, {u} updated.")
