"""Shared contract for foreign job portal sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


Emit = Callable[[str], None]


class JobSource(ABC):
    """Portal that returns jobs in extractor-compatible dict shape."""

    name: str = "base"

    @abstractmethod
    def search(
        self,
        queries: list[str],
        *,
        location: str = "Remote",
        days: int = 14,
        limit: int = 20,
        log: Emit | None = None,
    ) -> list[dict]:
        """Return list of job dicts ready for db.save_foreign_job."""
