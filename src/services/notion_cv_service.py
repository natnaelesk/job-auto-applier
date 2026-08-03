"""NotionCVService — CV generation + dual Notion database sync."""
from __future__ import annotations

from typing import Callable

import cv_generator
import notion_tracker

Emit = Callable[[str], None]


class NotionCVService:
    """Generate CVs and sync Ethiopia / Foreign Notion databases."""

    def __init__(self, log: Emit | None = None):
        self.log = log or print

    def generate_cvs(self) -> int:
        emit = self.log
        emit("[CV] Generating for matched jobs…")
        n = cv_generator.generate_for_matched(log=emit)
        emit(f"[CV] {n} CV(s) ready")
        return n

    def sync_notion(self, *, full: bool = False) -> dict:
        """Sync dirty jobs to the correct Notion DB by market."""
        emit = self.log
        eth = notion_tracker.sync_jobs(log=emit, full=full, market="ethiopia")
        foreign = notion_tracker.sync_jobs(log=emit, full=full, market="foreign")
        return {
            "ethiopia": {"created": eth[0], "updated": eth[1]},
            "foreign": {"created": foreign[0], "updated": foreign[1]},
        }

    def generate_and_sync(self, *, full: bool = False) -> dict:
        cvs = self.generate_cvs()
        sync = self.sync_notion(full=full)
        return {"cvs": cvs, **sync}
