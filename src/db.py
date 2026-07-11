"""SQLite storage: raw Telegram messages and structured jobs.

Dedup strategy: a job's identity is (company + title + link) normalized.
The same job re-posted on another day will not create a second row.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,          -- telegram message id
    channel TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    text TEXT NOT NULL,
    extracted INTEGER DEFAULT 0,     -- 0 = waiting for extraction, 1 = done
    UNIQUE(id, channel)
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    dedup_key TEXT UNIQUE NOT NULL,
    company TEXT,
    title TEXT,
    location TEXT,
    salary TEXT,
    experience TEXT,
    skills TEXT,                     -- JSON list
    link TEXT,
    apply_method TEXT,               -- url | email | telegram | unknown
    apply_target TEXT,               -- URL, email, or t.me handle when distinct from link
    description TEXT,
    status TEXT DEFAULT 'found',     -- found -> matched/skipped -> applying -> applied/manual/failed
    match_score INTEGER,
    match_reasons TEXT,              -- JSON list
    cv_path TEXT,
    notion_page_id TEXT,
    created_at TEXT NOT NULL,
    applied_at TEXT,
    screenshot_path TEXT,
    block_reason TEXT,
    apply_confidence TEXT,
    last_response_at TEXT,
    response_summary TEXT,
    notes TEXT,
    apply_answers TEXT                 -- JSON list of {label, answer}
);
"""

# Columns added after the initial schema — applied via ALTER on existing DBs.
_MIGRATIONS = [
    ("screenshot_path", "TEXT"),
    ("block_reason", "TEXT"),
    ("apply_confidence", "TEXT"),
    ("last_response_at", "TEXT"),
    ("response_summary", "TEXT"),
    ("apply_target", "TEXT"),
    ("notes", "TEXT"),
    ("apply_answers", "TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    for name, col_type in _MIGRATIONS:
        if name not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {col_type}")
    conn.commit()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def save_message(conn, msg_id: int, channel: str, posted_at: str, text: str) -> bool:
    """Returns True if the message was new."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO messages (id, channel, posted_at, text) VALUES (?, ?, ?, ?)",
        (msg_id, channel, posted_at, text),
    )
    conn.commit()
    return cur.rowcount > 0


def unextracted_messages(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM messages WHERE extracted = 0 ORDER BY posted_at"
    ).fetchall()


def mark_extracted(conn, msg_id: int) -> None:
    conn.execute("UPDATE messages SET extracted = 1 WHERE id = ?", (msg_id,))
    conn.commit()


def _dedup_key(company: str, title: str, link: str) -> str:
    basis = f"{(company or '').strip().lower()}|{(title or '').strip().lower()}|{(link or '').strip().lower()}"
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def save_job(conn, message_id: int, job: dict) -> bool:
    """Insert a structured job. Returns True if new, False if duplicate."""
    link = job.get("link")
    method = job.get("apply_method", "unknown")
    target = job.get("apply_target")
    # Keep a usable target in link when extractor only filled apply_target
    if not link and target:
        link = target
    if method == "email" and target and not link:
        link = target
    key = _dedup_key(job.get("company", ""), job.get("title", ""), link or "")
    cur = conn.execute(
        """INSERT OR IGNORE INTO jobs
           (message_id, dedup_key, company, title, location, salary, experience,
            skills, link, apply_method, apply_target, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            message_id,
            key,
            job.get("company"),
            job.get("title"),
            job.get("location"),
            job.get("salary"),
            job.get("experience"),
            json.dumps(job.get("skills", [])),
            link,
            method,
            target,
            job.get("description"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def jobs_with_status(conn, status: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY created_at", (status,)
    ).fetchall()


def status_counts(conn=None) -> dict[str, int]:
    """Return {status: count, ..., 'all': total} for dashboard counters."""
    own = conn is None
    if own:
        conn = connect()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
    ).fetchall()
    counts = {r["status"]: int(r["n"]) for r in rows}
    counts["all"] = sum(counts.values())
    if own:
        conn.close()
    return counts


def recent_jobs(conn=None, limit: int = 40) -> list[sqlite3.Row]:
    own = conn is None
    if own:
        conn = connect()
    rows = conn.execute(
        """
        SELECT id, company, title, status, match_score, salary, location,
               last_response_at, response_summary, applied_at, created_at
        FROM jobs
        ORDER BY COALESCE(last_response_at, applied_at, created_at) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    if own:
        conn.close()
    return rows


def recent_email_updates(conn=None, limit: int = 25) -> list[sqlite3.Row]:
    """Jobs that received a company reply / note."""
    own = conn is None
    if own:
        conn = connect()
    rows = conn.execute(
        """
        SELECT id, company, title, status, response_summary, last_response_at
        FROM jobs
        WHERE last_response_at IS NOT NULL AND last_response_at != ''
        ORDER BY last_response_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    if own:
        conn.close()
    return rows


def update_job(conn, job_id: int, **fields) -> None:
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))
    conn.commit()
