"""Job extractor: turns raw Telegram messages into structured job rows.

Primary path: AI extraction via the Cursor SDK (handles any post format).
Fallback path (no CURSOR_API_KEY yet): a basic regex extractor so the
pipeline stays testable - it finds links/emails and uses the first line as
the title, leaving the rest for the AI to redo later.
"""
import re

import ai
import config
import db

URL_RE = re.compile(r"https?://\S+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _fallback_extract(text: str) -> list[dict]:
    urls = URL_RE.findall(text)
    emails = EMAIL_RE.findall(text)
    link = urls[0].rstrip(").,") if urls else None
    if link:
        method, target = "url", link
    elif emails:
        method, target = "email", emails[0]
    else:
        method, target = "unknown", None

    first_line = text.strip().splitlines()[0][:120]
    return [{
        "company": None,
        "title": first_line,
        "location": None,
        "salary": None,
        "experience": None,
        "skills": [],
        "link": link,
        "apply_method": method,
        "apply_target": target,
        "description": text[:500],
    }]


BATCH_SIZE = 8


def _ai_extract_batch(messages) -> dict[int, list[dict]]:
    """Extract a batch of messages in one AI call. Returns {msg_id: [jobs]}."""
    blob = "\n\n".join(
        f"=== MESSAGE ID {m['id']} ===\n{m['text']}" for m in messages
    )
    prompt = ai.load_prompt("extract_job", messages=blob)
    result = ai.ask_json(prompt)
    if not isinstance(result, dict):
        raise ValueError(f"expected JSON object, got {type(result).__name__}")
    return {int(k): v for k, v in result.items() if isinstance(v, list)}


def extract_pending(use_ai: bool | None = None, log=None) -> tuple[int, int]:
    """Extract all unprocessed messages. Returns (messages_processed, jobs_found)."""
    if use_ai is None:
        use_ai = bool(config.CURSOR_API_KEY)
    emit = log or print

    conn = db.connect()
    messages = db.unextracted_messages(conn)
    jobs_found = 0
    processed = 0
    total = len(messages)
    emit(f"[Extract] {total} message(s) waiting")

    if total == 0:
        conn.close()
        emit("[Extract] Nothing to extract")
        return 0, 0

    if not use_ai:
        for msg in messages:
            for job in _fallback_extract(msg["text"]):
                if db.save_job(conn, msg["id"], job):
                    jobs_found += 1
            db.mark_extracted(conn, msg["id"])
            processed += 1
            if processed % 20 == 0 or processed == total:
                emit(f"[Extract] {processed}/{total} msgs · {jobs_found} jobs")
        conn.close()
        return processed, jobs_found

    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    for bi, start in enumerate(range(0, total, BATCH_SIZE), start=1):
        batch = messages[start : start + BATCH_SIZE]
        emit(f"[Extract] Batch {bi}/{batches} ({len(batch)} msgs)…")
        try:
            results = _ai_extract_batch(batch)
        except Exception as e:
            emit(f"[Extract] ! batch {bi} failed: {e}")
            continue
        batch_jobs = 0
        for msg in batch:
            for job in results.get(msg["id"], []):
                if db.save_job(conn, msg["id"], job):
                    jobs_found += 1
                    batch_jobs += 1
            db.mark_extracted(conn, msg["id"])
            processed += 1
        emit(
            f"[Extract] {processed}/{total} msgs · +{batch_jobs} this batch · "
            f"{jobs_found} jobs total"
        )

    conn.close()
    emit(f"[Extract] Done — {processed} msgs, {jobs_found} jobs")
    return processed, jobs_found


if __name__ == "__main__":
    processed, found = extract_pending()
    print(f"Processed {processed} message(s), found {found} new job(s).")
