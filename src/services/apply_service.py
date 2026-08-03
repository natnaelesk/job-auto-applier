"""ApplyService — apply queue across Ethiopia + foreign markets."""
from __future__ import annotations

from typing import Callable

from applier import agent as apply_agent

Emit = Callable[[str], None]


class ApplyService:
    """Wraps the human-orchestrated apply session helpers."""

    def __init__(self, log: Emit | None = None):
        self.log = log or print

    def load_queue(
        self,
        *,
        market: str | None = None,
        limit: int | None = None,
    ) -> list:
        """market: None/'all' | 'ethiopia' | 'foreign'."""
        m = None if not market or market == "all" else market
        jobs = apply_agent.load_apply_queue(limit=limit, market=m)
        emit = self.log
        label = m or "all"
        emit(f"[Apply] Queue ({label}): {len(jobs)} job(s)")
        return jobs

    def open_session(self):
        """Return a new ApplySession (UI drives it)."""
        return apply_agent.ApplySession(log=self.log)
