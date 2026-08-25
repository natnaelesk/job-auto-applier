"""In-memory apply session + ring log for the UI."""
from __future__ import annotations

import threading
import webbrowser
from collections import deque
from datetime import datetime, timezone
from typing import Any

from . import notion_store
from .mapping import Board


class LogBus:
    def __init__(self, maxlen: int = 400):
        self._lock = threading.Lock()
        self._entries: deque[dict[str, str]] = deque(maxlen=maxlen)

    def emit(self, message: str, level: str = "info") -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": level,
            "message": message,
        }
        with self._lock:
            self._entries.append(entry)

    def snapshot(self) -> list[dict[str, str]]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


logs = LogBus()


class ApplySession:
    """Human-controlled apply loop. No auto-submit."""

    def __init__(self):
        self._lock = threading.Lock()
        self.board: Board | None = None
        self.active = False
        self.queue: list[dict] = []
        self.index = 0
        self.show_cover = False

    def start(self, board: Board, page_id: str | None = None) -> dict:
        with self._lock:
            rows = notion_store.list_ready(board)
            # Prefer rows that already have a CV for applying; still show all Ready
            self.board = board
            self.queue = rows
            self.active = True
            self.show_cover = False
            self.index = 0
            if page_id:
                for i, r in enumerate(rows):
                    if r["page_id"] == page_id:
                        self.index = i
                        break
            logs.emit(f"[Apply] Started {board} — {len(rows)} Ready row(s)")
            return self.state()

    def stop(self) -> dict:
        with self._lock:
            self.active = False
            logs.emit("[Apply] Session stopped")
            return self.state()

    def state(self) -> dict:
        current = None
        if self.queue and 0 <= self.index < len(self.queue):
            current = self.queue[self.index]
        return {
            "board": self.board or "mik",
            "active": self.active,
            "index": self.index,
            "total": len(self.queue),
            "current": current,
            "show_cover": self.show_cover,
        }

    def current(self) -> dict | None:
        st = self.state()
        return st["current"]

    def refresh_current(self) -> dict | None:
        with self._lock:
            if not self.board or not self.queue:
                return None
            page_id = self.queue[self.index]["page_id"]
            row = notion_store.get_page(self.board, page_id)
            self.queue[self.index] = row
            return row

    def next_job(self) -> dict:
        with self._lock:
            if self.index + 1 >= len(self.queue):
                logs.emit("[Apply] End of queue")
                self.active = False
                return self.state()
            self.index += 1
            self.show_cover = False
            cur = self.queue[self.index]
            logs.emit(
                f"[Apply] Next → {cur.get('company') or cur.get('name')} "
                f"— {cur.get('role') or cur.get('name')}"
            )
            return self.state()

    def toggle_cover(self) -> dict:
        with self._lock:
            self.show_cover = not self.show_cover
            return self.state()

    def open_link(self) -> dict:
        cur = self.current()
        if not cur:
            logs.emit("[Apply] No current row", "error")
            return {"ok": False, "url": None}
        link = (cur.get("apply_link") or "").strip()
        if not link:
            logs.emit("[Apply] No Apply link on this row", "error")
            return {"ok": False, "url": None}
        try:
            webbrowser.open(link, new=2)
            logs.emit(f"[Apply] Opened {link}")
        except Exception as e:
            logs.emit(f"[Apply] Open failed ({e}) — copy the link instead", "warn")
        return {"ok": True, "url": link}


session = ApplySession()
