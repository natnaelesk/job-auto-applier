"""Phase 4 - Notion tracker.

One colorful database tracks every job the agent touches. First run creates
the database automatically inside the page you've shared with the integration
and saves its ID to .env. Every later run syncs job statuses into it.
"""
import json
from pathlib import Path

from notion_client import Client

import config
import db

# Pin a stable API version (classic database endpoints)
NOTION_VERSION = "2022-06-28"

DB_TITLE = "Job Applications Tracker"

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
}


def _client() -> Client:
    token = config.require("NOTION_TOKEN", config.NOTION_TOKEN)
    return Client(auth=token, notion_version=NOTION_VERSION)


def _save_database_id(database_id: str) -> None:
    """Persist the created database id into .env so we never create twice."""
    env_path = config.PROJECT_ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("NOTION_DATABASE_ID"):
            lines[i] = f"NOTION_DATABASE_ID={database_id}"
            break
    else:
        lines.append(f"NOTION_DATABASE_ID={database_id}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    config.NOTION_DATABASE_ID = database_id


def ensure_database(notion: Client) -> str:
    """Return the tracker database id, creating the database on first run."""
    if config.NOTION_DATABASE_ID:
        _ensure_number_column(notion, config.NOTION_DATABASE_ID)
        _ensure_notes_column(notion, config.NOTION_DATABASE_ID)
        return config.NOTION_DATABASE_ID

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
            "icon": {"type": "emoji", "emoji": "🎯"},
            "title": [{"type": "text", "text": {"content": DB_TITLE}}],
            "properties": DB_PROPERTIES,
        },
    )
    _save_database_id(created["id"])
    print(f"  Created Notion database '{DB_TITLE}' (id saved to .env)")
    return created["id"]


def _ensure_number_column(notion: Client, database_id: str) -> None:
    """Add the '#' counter column to an existing database if missing."""
    try:
        db_obj = notion.request(path=f"databases/{database_id}", method="GET")
    except Exception as e:
        print(f"  ! could not read Notion database schema: {e}")
        return

    props = db_obj.get("properties") or {}
    if "#" in props:
        return

    try:
        notion.request(
            path=f"databases/{database_id}",
            method="PATCH",
            body={"properties": {"#": {"number": {"format": "number"}}}},
        )
        print("  Added '#' number column to Notion database")
    except Exception as e:
        print(f"  ! could not add '#' column: {e}")


def _ensure_notes_column(notion: Client, database_id: str) -> None:
    try:
        db_obj = notion.request(path=f"databases/{database_id}", method="GET")
    except Exception:
        return
    props = db_obj.get("properties") or {}
    if "Notes" in props:
        return
    try:
        notion.request(
            path=f"databases/{database_id}",
            method="PATCH",
            body={"properties": {"Notes": {"rich_text": {}}}},
        )
        print("  Added 'Notes' column to Notion database")
    except Exception as e:
        print(f"  ! could not add Notes column: {e}")


def _rt(text) -> dict:
    return {"rich_text": [{"text": {"content": str(text)[:2000]}}]} if text else {"rich_text": []}


def _job_properties(job) -> dict:
    label, _ = STATUS_META.get(job["status"], STATUS_META["found"])
    reasons = json.loads(job["match_reasons"]) if job["match_reasons"] else []
    props = {
        "#": {"number": job["id"]},
        "Company": {"title": [{"text": {"content": job["company"] or "Unknown"}}]},
        "Role": _rt(job["title"]),
        "Status": {"select": {"name": label}},
        "Match Reasons": _rt("\n".join(f"• {r}" for r in reasons) if reasons else None),
        "Location": _rt(job["location"]),
        "Salary": _rt(job["salary"]),
        "CV Used": _rt(Path(job["cv_path"]).name if job["cv_path"] else None),
    }
    if job["match_score"] is not None:
        props["Match Score"] = {"number": job["match_score"] / 100}
    if job["link"]:
        props["Link"] = {"url": job["link"]}
    if job["applied_at"]:
        props["Applied Date"] = {"date": {"start": job["applied_at"][:10]}}
    keys = job.keys() if hasattr(job, "keys") else []
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


def sync_one_job(job_id: int) -> bool:
    """Push a single job to Notion. Returns True on success."""
    notion = _client()
    database_id = ensure_database(notion)
    conn = db.connect()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        return False
    props = _job_properties(job)
    try:
        if job["notion_page_id"]:
            notion.pages.update(page_id=job["notion_page_id"], properties=props)
        else:
            page = notion.pages.create(
                parent={"database_id": database_id}, properties=props
            )
            db.update_job(conn, job_id, notion_page_id=page["id"])
        conn.close()
        return True
    except Exception as e:
        print(f"  ! Notion sync failed for job {job_id}: {e}")
        conn.close()
        return False


def sync_jobs(log=None) -> tuple[int, int]:
    """Push every job to Notion. Creates pages for new jobs, updates the rest.
    Returns (created, updated)."""
    emit = log or print
    emit("[Notion] Connecting…")
    notion = _client()
    database_id = ensure_database(notion)

    conn = db.connect()
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    total = len(jobs)
    created = updated = failed = 0
    emit(f"[Notion] Syncing {total} job(s)…")
    if total == 0:
        conn.close()
        emit("[Notion] Nothing to sync")
        return 0, 0

    for i, job in enumerate(jobs, start=1):
        props = _job_properties(job)
        title = (job["title"] or "?").encode("ascii", "replace").decode()
        try:
            if job["notion_page_id"]:
                notion.pages.update(page_id=job["notion_page_id"], properties=props)
                updated += 1
                action = "updated"
            else:
                page = notion.pages.create(
                    parent={"database_id": database_id}, properties=props
                )
                db.update_job(conn, job["id"], notion_page_id=page["id"])
                created += 1
                action = "created"
            if i % 10 == 0 or i == total:
                emit(
                    f"[Notion] {i}/{total} · {action} #{job['id']} · "
                    f"created={created} updated={updated}"
                )
        except Exception as e:
            failed += 1
            emit(f"[Notion] ! {i}/{total} failed #{job['id']} ({title}): {e}")

    conn.close()
    emit(
        f"[Notion] Done — {created} created, {updated} updated"
        + (f", {failed} failed" if failed else "")
    )
    return created, updated


if __name__ == "__main__":
    c, u = sync_jobs()
    print(f"\nNotion: {c} page(s) created, {u} updated.")
