"""SearchService — Ethiopia Telegram scan + foreign portal search."""
from __future__ import annotations

import asyncio
from typing import Callable

import config
import db
import extractor
import matcher
import telegram_watcher
from sources.freehire import FreehireSource
from sources.linkedin import LinkedInSource

Emit = Callable[[str], None]


class SearchService:
    """Owns job intake for both markets."""

    def __init__(self, log: Emit | None = None):
        self.log = log or print

    def scan_ethiopia(self) -> dict:
        """Telegram scan → extract. Returns counts."""
        emit = self.log
        emit("[Search] Ethiopia: scanning Telegram…")
        count = asyncio.run(telegram_watcher.scan_channel(log=emit))
        enriched = asyncio.run(telegram_watcher.resolve_source_links(log=emit))
        emit(f"[Search] Ethiopia: {count} new msg(s), {enriched} enriched")
        processed, found = extractor.extract_pending(log=emit)
        emit(f"[Search] Ethiopia: extracted {processed} msg(s) → {found} job(s)")
        return {
            "messages": count,
            "enriched": enriched,
            "processed": processed,
            "jobs": found,
        }

    def search_foreign(
        self,
        *,
        queries: list[str] | None = None,
        location: str | None = None,
        days: int | None = None,
        limit: int | None = None,
        match: bool = True,
    ) -> dict:
        """Run freehire (+ LinkedIn) → save foreign jobs → optionally match."""
        emit = self.log
        queries = queries or config.foreign_search_queries()
        location = location or config.FOREIGN_SEARCH_LOCATION
        days = days if days is not None else config.FOREIGN_SEARCH_DAYS
        limit = limit if limit is not None else config.FOREIGN_SEARCH_LIMIT

        emit(
            f"[Search] Foreign: queries={queries} location={location!r} "
            f"days={days} limit={limit}"
        )

        collected: list[dict] = []
        if config.FREEHIRE_ENABLED:
            try:
                fh = FreehireSource()
                collected.extend(
                    fh.search(
                        queries,
                        location=location,
                        days=days,
                        limit=limit,
                        log=emit,
                    )
                )
            except Exception as e:
                emit(f"[Search] ! freehire failed: {e}")
        else:
            emit("[Search] freehire disabled")

        if config.LINKEDIN_ENABLED:
            try:
                # Keep LinkedIn gentle: fewer queries / lower limit
                li_queries = queries[:2]
                li_limit = min(limit, 8)
                li = LinkedInSource()
                collected.extend(
                    li.search(
                        li_queries,
                        location=location,
                        days=days,
                        limit=li_limit,
                        log=emit,
                    )
                )
            except Exception as e:
                emit(f"[Search] ! linkedin failed: {e}")
        else:
            emit("[Search] linkedin disabled")

        # Dedup within this run by link
        by_link: dict[str, dict] = {}
        for job in collected:
            link = (job.get("link") or "").strip().lower()
            key = link or f"{job.get('company')}|{job.get('title')}"
            by_link[key] = job
        unique = list(by_link.values())

        conn = db.connect()
        saved = 0
        for job in unique:
            if db.save_foreign_job(conn, job):
                saved += 1
        conn.close()
        emit(f"[Search] Foreign: {len(unique)} unique, {saved} new saved")

        match_counts: dict = {}
        if match and saved > 0:
            emit("[Search] Matching foreign jobs…")
            match_counts = matcher.match_pending(log=emit)
            emit(f"[Search] Match result: {match_counts}")
        elif match:
            # Still match any leftover 'found' foreign/ethiopia jobs
            match_counts = matcher.match_pending(log=emit)

        return {
            "fetched": len(collected),
            "unique": len(unique),
            "saved": saved,
            "match": match_counts,
        }
