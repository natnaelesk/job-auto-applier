"""Phase 6 — Gmail scanner.

Reads inbox since last scan, classifies replies against applied jobs,
updates SQLite + leaves Notion sync to pick up status/summary fields.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import ai
import config
import db
import state

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = config.PROJECT_ROOT / "token.json"


def _credentials_path() -> Path:
    raw = config.GMAIL_CREDENTIALS_FILE or "credentials.json"
    path = Path(raw)
    if not path.is_absolute():
        path = config.PROJECT_ROOT / path
    return path


def _get_gmail_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_file = _credentials_path()
            if not cred_file.exists():
                raise SystemExit(
                    f"Missing Gmail OAuth file: {cred_file}\n"
                    "Download a Desktop OAuth client JSON from Google Cloud Console "
                    "and set GMAIL_CREDENTIALS_FILE in .env"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _header(headers: list[dict], name: str) -> str:
    name_l = name.lower()
    for h in headers:
        if (h.get("name") or "").lower() == name_l:
            return h.get("value") or ""
    return ""


def _list_messages_since(service, since: datetime) -> list[dict]:
    """Return lightweight email dicts newer than `since`."""
    # Gmail search uses epoch seconds
    after = int(since.timestamp())
    query = f"after:{after} -category:promotions -category:social"
    messages: list[dict] = []
    page_token = None

    while True:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=50)
            .execute()
        )
        for meta in resp.get("messages", []):
            full = (
                service.users()
                .messages()
                .get(userId="me", id=meta["id"], format="metadata",
                     metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
            headers = full.get("payload", {}).get("headers", [])
            messages.append(
                {
                    "email_id": full["id"],
                    "from": _header(headers, "From"),
                    "subject": _header(headers, "Subject"),
                    "date": _header(headers, "Date"),
                    "snippet": full.get("snippet") or "",
                }
            )
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return messages


def _applied_jobs_blob(conn) -> tuple[str, set[int]]:
    rows = conn.execute(
        """
        SELECT id, company, title, link, status
        FROM jobs
        WHERE status IN ('applied', 'applying', 'manual', 'interview', 'offer')
        ORDER BY id
        """
    ).fetchall()
    lines = []
    ids = set()
    for r in rows:
        ids.add(r["id"])
        lines.append(
            f"- id={r['id']} | {r['company']} | {r['title']} | {r['status']} | {r['link'] or ''}"
        )
    return "\n".join(lines) or "(none)", ids


def scan_inbox(log=None) -> dict:
    """Scan Gmail and update matching jobs. Returns summary counts."""
    emit = log or print
    counts = {"emails": 0, "matched": 0, "updated": 0, "ignored": 0, "failed": 0}

    since = state.get_last_scan("gmail")
    emit(f"[Gmail] Scan since {since.isoformat()}")

    try:
        service = _get_gmail_service()
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"Gmail auth failed: {e}") from e

    emails = _list_messages_since(service, since)
    counts["emails"] = len(emails)
    now = datetime.now(timezone.utc)
    emit(f"[Gmail] {len(emails)} new email(s)")

    if not emails:
        state.set_last_scan("gmail", now)
        emit("[Gmail] No new emails")
        return counts

    conn = db.connect()
    jobs_blob, valid_ids = _applied_jobs_blob(conn)

    # Batch emails for the classifier
    BATCH = 15
    batches = (len(emails) + BATCH - 1) // BATCH
    for bi, start in enumerate(range(0, len(emails), BATCH), start=1):
        batch = emails[start : start + BATCH]
        emit(f"[Gmail] Batch {bi}/{batches} ({len(batch)} emails)…")
        email_blob = "\n\n".join(
            (
                f"=== EMAIL ID {e['email_id']} ===\n"
                f"From: {e['from']}\n"
                f"Subject: {e['subject']}\n"
                f"Date: {e['date']}\n"
                f"Snippet: {e['snippet']}"
            )
            for e in batch
        )
        prompt = ai.load_prompt(
            "classify_email",
            jobs=jobs_blob,
            emails=email_blob,
        )
        try:
            payload = ai.ask_json(prompt)
            results = payload.get("results", payload) if isinstance(payload, dict) else payload
            if not isinstance(results, list):
                raise ValueError("expected results list")
        except Exception as e:
            emit(f"[Gmail] ! classify batch {bi} failed: {e}")
            counts["failed"] += len(batch)
            continue

        by_id = {
            str(r.get("email_id")): r
            for r in results
            if isinstance(r, dict) and r.get("email_id")
        }

        for email in batch:
            verdict = by_id.get(email["email_id"], {})
            job_id = verdict.get("job_id")
            new_status = verdict.get("status")
            summary = verdict.get("summary") or ""

            if not job_id or job_id not in valid_ids:
                counts["ignored"] += 1
                continue

            counts["matched"] += 1
            fields = {
                "last_response_at": now.isoformat(),
                "response_summary": summary[:500] if summary else None,
            }
            # Only change status for interview/rejected/offer
            if new_status in {"interview", "rejected", "offer"}:
                fields["status"] = new_status
                counts["updated"] += 1
                emit(f"[Gmail] [{new_status}] job #{job_id}: {summary[:80]}")
            elif summary:
                counts["updated"] += 1
                emit(f"[Gmail] [note] job #{job_id}: {summary[:80]}")

            db.update_job(conn, int(job_id), **fields)

        emit(
            f"[Gmail] Progress · matched={counts['matched']} "
            f"updated={counts['updated']} ignored={counts['ignored']} "
            f"failed={counts['failed']}"
        )

    conn.close()
    state.set_last_scan("gmail", now)
    emit(f"[Gmail] Done — {counts}")
    return counts


if __name__ == "__main__":
    print(scan_inbox())
