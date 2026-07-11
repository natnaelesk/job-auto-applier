"""Persistent run state: remembers last-scanned dates so every run picks up
exactly where the previous one stopped (resumable, no duplicates, no gaps)."""
import json
from datetime import datetime, timedelta, timezone

from config import STATE_PATH, FIRST_SCAN_DAYS


def _load() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _save(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_last_scan(key: str) -> datetime:
    """Returns last scan time for 'telegram' or 'gmail' (UTC).
    First ever run: FIRST_SCAN_DAYS ago."""
    state = _load()
    raw = state.get(f"last_{key}_scan")
    if raw:
        return datetime.fromisoformat(raw)
    return datetime.now(timezone.utc) - timedelta(days=FIRST_SCAN_DAYS)


def set_last_scan(key: str, when: datetime) -> None:
    state = _load()
    state[f"last_{key}_scan"] = when.isoformat()
    _save(state)
