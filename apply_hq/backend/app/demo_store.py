"""In-memory demo fixtures when APPLY_HQ_DEMO=1 AND no live Notion token.

Never writes to Notion. Used for UI smoke / walkthrough only.

CRITICAL: a live NOTION_TOKEN always wins — demo must not hide real Mik/Spark data.
"""
from __future__ import annotations

import os
from copy import deepcopy
from datetime import datetime, timezone

_DEMO_MIK = [
    {
        "board": "mik",
        "page_id": "demo-mik-1",
        "url": "https://www.notion.so/demo-mik-1",
        "name": "Acme — Backend Engineer",
        "company": "Acme",
        "role": "Backend Engineer",
        "status": "Ready",
        "apply_link": "https://example.com/jobs/acme-backend",
        "source": "WWR",
        "location": "Remote",
        "remote": True,
        "stack": "Python, FastAPI, Postgres",
        "salary": "$120k",
        "why": "Strong backend fit",
        "cv_path": None,
        "has_cv": False,
        "cover_letter": None,
        "applied_date": None,
        "local_id": 1,
        "notes": None,
        "client": None,
        "platform": None,
        "budget": None,
        "package": None,
    },
    {
        "board": "mik",
        "page_id": "demo-mik-2",
        "url": "https://www.notion.so/demo-mik-2",
        "name": "Globex — Full Stack",
        "company": "Globex",
        "role": "Full Stack Developer",
        "status": "Ready",
        "apply_link": "https://example.com/jobs/globex-fs",
        "source": "RemoteOK",
        "location": "Remote",
        "remote": True,
        "stack": "React, Node, TypeScript",
        "salary": "",
        "why": "Stack match",
        "cv_path": "/tmp/demo/CV_Natnael_Globex.pdf",
        "has_cv": True,
        "cover_letter": None,
        "applied_date": None,
        "local_id": 2,
        "notes": None,
        "client": None,
        "platform": None,
        "budget": None,
        "package": None,
    },
]

_DEMO_SPARK = [
    {
        "board": "spark",
        "page_id": "demo-spark-1",
        "url": "https://www.notion.so/demo-spark-1",
        "name": "Landing page redesign",
        "company": "Northwind",
        "role": "Landing page redesign",
        "status": "Ready",
        "apply_link": "https://www.upwork.com/jobs/~demo",
        "source": None,
        "location": None,
        "remote": None,
        "stack": "React, Tailwind",
        "salary": None,
        "why": "Portfolio match",
        "cv_path": None,
        "has_cv": False,
        "cover_letter": None,
        "applied_date": None,
        "local_id": "spark-1",
        "notes": None,
        "client": "Northwind",
        "platform": "Upwork",
        "budget": "$800",
        "package": "Web",
    },
]

_store = {
    "mik": deepcopy(_DEMO_MIK),
    "spark": deepcopy(_DEMO_SPARK),
}


def _flag_on() -> bool:
    return os.getenv("APPLY_HQ_DEMO", "").strip().lower() in {"1", "true", "yes"}


def force_enabled() -> bool:
    """True only when DEMO is requested AND there is no live Notion token.

    A configured NOTION_TOKEN always takes precedence — never serve Acme/Globex
    fixtures over real Mik/Spark Ready rows.
    """
    from . import config

    if (config.NOTION_TOKEN or "").strip():
        return False
    return _flag_on()


def demo_flag_ignored_because_token() -> bool:
    """True when user set APPLY_HQ_DEMO but a live token disabled it."""
    from . import config

    return _flag_on() and bool((config.NOTION_TOKEN or "").strip())


def list_ready(board: str) -> list[dict]:
    return [deepcopy(r) for r in _store[board] if r.get("status") == "Ready"]


def list_needs_cv(board: str) -> list[dict]:
    return [deepcopy(r) for r in _store[board] if not r.get("has_cv")]


def get_page(board: str, page_id: str) -> dict:
    for r in _store[board]:
        if r["page_id"] == page_id:
            return deepcopy(r)
    raise KeyError(page_id)


def mark_status(board: str, page_id: str, status: str, notes: str | None = None) -> dict:
    for r in _store[board]:
        if r["page_id"] == page_id:
            r["status"] = status
            if notes is not None:
                r["notes"] = notes
            if status == "Applied":
                r["applied_date"] = datetime.now(timezone.utc).date().isoformat()
            return deepcopy(r)
    raise KeyError(page_id)


def write_cv(board: str, page_id: str, cv_path: str) -> dict:
    for r in _store[board]:
        if r["page_id"] == page_id:
            r["cv_path"] = cv_path
            r["has_cv"] = True
            return deepcopy(r)
    raise KeyError(page_id)


def write_cover(board: str, page_id: str, cover_path: str) -> dict:
    for r in _store[board]:
        if r["page_id"] == page_id:
            r["cover_letter"] = cover_path
            return deepcopy(r)
    raise KeyError(page_id)
