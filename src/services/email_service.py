"""EmailService — Gmail reply scanner for both markets."""
from __future__ import annotations

from typing import Callable

import gmail_scanner

Emit = Callable[[str], None]


class EmailService:
    """Scan inbox and attach replies to applied jobs (any market)."""

    def __init__(self, log: Emit | None = None):
        self.log = log or print

    def scan(self) -> dict:
        emit = self.log
        emit("[Email] Scanning Gmail for company replies (both markets)…")
        counts = gmail_scanner.scan_inbox(log=emit)
        emit(f"[Email] Done: {counts}")
        return counts
