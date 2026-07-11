"""Phase 1 - Telegram watcher.

Connects to every configured channel and saves messages posted since that
channel's last scan into SQLite. First run asks for phone + login code once;
the session is stored in data/telegram.session and reused forever.
"""
import asyncio
import re
from datetime import datetime, timezone

from telethon import TelegramClient
from telethon.tl.types import KeyboardButtonUrl, MessageEntityTextUrl

import config
import db
import state


def _full_text(msg) -> str:
    """Message text plus any URLs hiding in inline buttons or hyperlinked text.
    Many channels put the apply link in a button - invisible in msg.text."""
    parts = [msg.text or ""]
    urls = []

    if msg.entities:
        for entity in msg.entities:
            if isinstance(entity, MessageEntityTextUrl) and entity.url:
                urls.append(entity.url)

    if msg.reply_markup and hasattr(msg.reply_markup, "rows"):
        for row in msg.reply_markup.rows:
            for button in row.buttons:
                if isinstance(button, KeyboardButtonUrl) and button.url:
                    urls.append(f"{button.text}: {button.url}" if button.text else button.url)

    if urls:
        parts.append("\n[Links in this post]:")
        parts.extend(urls)
    return "\n".join(parts)


async def _scan_one(client: TelegramClient, channel: str) -> int:
    """Fetch new messages for one channel since its last scan."""
    since = state.get_last_scan(f"telegram:{channel}")
    scan_started = datetime.now(timezone.utc)
    new_count = 0

    conn = db.connect()
    try:
        async for msg in client.iter_messages(channel):
            if msg.date < since:
                break
            if not msg.text:
                continue
            if db.save_message(
                conn, msg.id, channel, msg.date.isoformat(), _full_text(msg)
            ):
                new_count += 1
    finally:
        conn.close()

    state.set_last_scan(f"telegram:{channel}", scan_started)
    return new_count


async def scan_channel(log=None) -> int:
    """Scan all configured Telegram channels. Returns total new messages saved."""
    emit = log or print
    api_id = int(config.require("TELEGRAM_API_ID", config.TELEGRAM_API_ID))
    api_hash = config.require("TELEGRAM_API_HASH", config.TELEGRAM_API_HASH)
    channels = config.telegram_channels()
    if not channels:
        raise SystemExit(
            "Missing TELEGRAM_CHANNELS (or TELEGRAM_CHANNEL) in .env"
        )

    total = 0
    n_ch = len(channels)
    emit(f"[Scan] {n_ch} channel(s)…")
    client = TelegramClient(config.TELEGRAM_SESSION, api_id, api_hash)
    async with client:
        for i, channel in enumerate(channels, start=1):
            emit(f"[Scan] {i}/{n_ch} {channel}…")
            try:
                n = await _scan_one(client, channel)
                emit(f"[Scan] {i}/{n_ch} {channel}: {n} new")
                total += n
            except Exception as e:
                emit(f"[Scan] ! {channel} failed: {e}")

    # Keep legacy key updated for older tooling
    state.set_last_scan("telegram", datetime.now(timezone.utc))
    emit(f"[Scan] Done — {total} new message(s)")
    return total


T_ME_RE = re.compile(r"https?://t\.me/([\w+]+)/(\d+)")


async def resolve_source_links(log=None) -> int:
    """Aggregator posts often link to the original channel post ('View on
    source') instead of carrying the apply link themselves. For unextracted
    messages whose only links are t.me post links, fetch the source post and
    append its content. Returns number of messages enriched."""
    emit = log or print
    api_id = int(config.TELEGRAM_API_ID)
    api_hash = config.TELEGRAM_API_HASH

    conn = db.connect()
    rows = conn.execute(
        "SELECT id, text FROM messages WHERE extracted = 0 "
        "AND text NOT LIKE '%[Source post]%'"
    ).fetchall()

    targets = []
    for r in rows:
        links = T_ME_RE.findall(r["text"])
        has_external = any(
            "t.me/" not in u for u in re.findall(r"https?://\S+", r["text"])
        )
        if links and not has_external:
            targets.append((r["id"], links[0][0], int(links[0][1])))

    total = len(targets)
    if not targets:
        conn.close()
        emit("[Scan] No source links to enrich")
        return 0

    emit(f"[Scan] Enriching {total} message(s) from source posts…")
    enriched = 0
    client = TelegramClient(config.TELEGRAM_SESSION, api_id, api_hash)
    async with client:
        for i, (msg_id, src_channel, src_id) in enumerate(targets, start=1):
            try:
                src = await client.get_messages(src_channel, ids=src_id)
                if not src or not src.text:
                    continue
                extra = _full_text(src)
                row = conn.execute(
                    "SELECT text FROM messages WHERE id = ?", (msg_id,)
                ).fetchone()
                if not row:
                    continue
                merged = f"{row['text']}\n\n[Source post @{src_channel}/{src_id}]:\n{extra}"
                conn.execute(
                    "UPDATE messages SET text = ? WHERE id = ?", (merged, msg_id)
                )
                enriched += 1
                if i % 10 == 0 or i == total:
                    emit(f"[Scan] Enrich {i}/{total} · {enriched} done")
            except Exception as e:
                emit(f"[Scan] ! enrich {msg_id} from @{src_channel}/{src_id}: {e}")
        conn.commit()
    conn.close()
    emit(f"[Scan] Enrich done — {enriched}/{total}")
    return enriched
