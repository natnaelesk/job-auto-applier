"""Locked Notion property mapping for Mik Jobs and Spark Projects.

Do not invent columns. Do not use old Job Hunt lists.
Smoke-tested in backend/tests/test_property_mapping.py.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

Board = Literal["mik", "spark"]

MIK_STATUS = {
    "Found",
    "Ready",
    "Applied",
    "Later",
    "Closed",
    "Reply",
    "Interview",
    "Offer",
    "Rejected",
}
SPARK_STATUS = {
    "Found",
    "Ready",
    "Applied",
    "Later",
    "Closed",
    "Reply",
    "Won",
    "Lost",
}
ACTION_STATUS = {"Applied", "Closed", "Later"}

# Exact property names — locked to live Notion schemas
MIK_PROPS = {
    "name": "Name",
    "company": "Company",
    "role": "Role",
    "status": "Status",
    "apply_link": "Apply link",
    "source": "Source",
    "location": "Location",
    "remote": "Remote",
    "stack": "Stack",
    "salary": "Salary",
    "why": "Why keep",
    "cv_path": "CV path",
    "has_cv": "Has CV",
    "cover_letter": "Cover letter",
    "applied_date": "Applied date",
    "local_id": "Local id",
    "notes": "Notes",
}

SPARK_PROPS = {
    "name": "Name",
    "company": "Client",  # Client stands in for company in UI
    "role": "Name",  # title is the project name; Role not present
    "client": "Client",
    "platform": "Platform",
    "status": "Status",
    "apply_link": "Apply link",
    "budget": "Budget",
    "stack": "Stack",
    "package": "Package",
    "why": "Why it fits",
    "cv_path": "CV path",
    "has_cv": "Has CV",
    "cover_letter": "Cover letter",
    "applied_date": "Applied date",
    "local_id": "Local id",
    "notes": "Notes",
}


def props_for(board: Board) -> dict[str, str]:
    return MIK_PROPS if board == "mik" else SPARK_PROPS


def allowed_status(board: Board) -> set[str]:
    return MIK_STATUS if board == "mik" else SPARK_STATUS


def _plain(rich: Any) -> str:
    if rich is None:
        return ""
    if isinstance(rich, str):
        return rich
    if isinstance(rich, list):
        parts = []
        for block in rich:
            if isinstance(block, dict):
                parts.append(block.get("plain_text") or block.get("text", {}).get("content", ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(rich)


def _title(prop: dict | None) -> str:
    if not prop:
        return ""
    return _plain(prop.get("title"))


def _rich(prop: dict | None) -> str:
    if not prop:
        return ""
    return _plain(prop.get("rich_text"))


def _select(prop: dict | None) -> str | None:
    if not prop:
        return None
    sel = prop.get("select")
    if not sel:
        return None
    return sel.get("name")


def _url(prop: dict | None) -> str | None:
    if not prop:
        return None
    return prop.get("url")


def _checkbox(prop: dict | None) -> bool:
    if not prop:
        return False
    return bool(prop.get("checkbox"))


def _number(prop: dict | None) -> float | int | None:
    if not prop:
        return None
    return prop.get("number")


def _date_start(prop: dict | None) -> str | None:
    if not prop:
        return None
    d = prop.get("date")
    if not d:
        return None
    return d.get("start")


def page_id_from_url(url: str) -> str:
    """Extract a Notion page UUID from an app.notion.com / notion.so URL."""
    import re

    raw = (url or "").rstrip("/").split("?")[0]
    # Prefer trailing 32-hex id
    m = re.search(r"([0-9a-fA-F]{32})$", raw.replace("-", ""))
    # URLs often have dashed or undashed id after last /
    m2 = re.search(r"([0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12})", raw)
    token = None
    if m2:
        token = m2.group(1).replace("-", "")
    elif m:
        token = m.group(1)
    if not token or len(token) != 32:
        raise ValueError(f"Cannot parse Notion page id from URL: {url!r}")
    return f"{token[0:8]}-{token[8:12]}-{token[12:16]}-{token[16:20]}-{token[20:32]}"


def parse_page(board: Board, page: dict) -> dict[str, Any]:
    """Map a Notion page object → Apply HQ row dict."""
    props = page.get("properties") or {}
    P = props_for(board)
    page_id = page.get("id") or ""
    url = page.get("url") or ""

    name = _title(props.get(P["name"]))
    status = _select(props.get(P["status"]))
    apply_link = _url(props.get(P["apply_link"]))
    cv_path = _rich(props.get(P["cv_path"]))
    has_cv = _checkbox(props.get(P["has_cv"]))
    cover = _rich(props.get(P["cover_letter"]))
    notes = _rich(props.get(P["notes"]))
    stack = _rich(props.get(P["stack"]))
    why = _rich(props.get(P["why"]))
    applied = _date_start(props.get(P["applied_date"]))

    if board == "mik":
        company = _rich(props.get(P["company"]))
        role = _rich(props.get(P["role"]))
        local_id = _number(props.get(P["local_id"]))
        return {
            "board": "mik",
            "page_id": page_id,
            "url": url,
            "name": name,
            "company": company,
            "role": role,
            "status": status,
            "apply_link": apply_link,
            "source": _select(props.get(P["source"])),
            "location": _rich(props.get(P["location"])),
            "remote": _checkbox(props.get(P["remote"])),
            "stack": stack,
            "salary": _rich(props.get(P["salary"])),
            "why": why,
            "cv_path": cv_path or None,
            "has_cv": has_cv,
            "cover_letter": cover or None,
            "applied_date": applied,
            "local_id": local_id,
            "notes": notes or None,
            "platform": None,
            "budget": None,
            "package": None,
            "client": None,
        }

    client = _rich(props.get(P["client"]))
    local_id = _rich(props.get(P["local_id"]))
    return {
        "board": "spark",
        "page_id": page_id,
        "url": url,
        "name": name,
        "company": client,  # UI "company" column
        "role": name,
        "client": client,
        "platform": _select(props.get(P["platform"])),
        "status": status,
        "apply_link": apply_link,
        "budget": _rich(props.get(P["budget"])),
        "stack": stack,
        "package": _rich(props.get(P["package"])),
        "why": why,
        "cv_path": cv_path or None,
        "has_cv": has_cv,
        "cover_letter": cover or None,
        "applied_date": applied,
        "local_id": local_id or None,
        "notes": notes or None,
        "source": None,
        "location": None,
        "remote": None,
        "salary": None,
    }


def rich_text(value: str) -> dict:
    text = (value or "")[:2000]
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


def select_prop(name: str) -> dict:
    return {"select": {"name": name}}


def checkbox_prop(checked: bool) -> dict:
    return {"checkbox": bool(checked)}


def date_prop(day: str | date | datetime | None) -> dict:
    if day is None:
        return {"date": None}
    if isinstance(day, datetime):
        start = day.date().isoformat()
    elif isinstance(day, date):
        start = day.isoformat()
    else:
        start = str(day)[:10]
    return {"date": {"start": start}}


def build_status_update(
    board: Board,
    status: str,
    *,
    notes: str | None = None,
    cover_letter: str | None = None,
) -> dict:
    """Properties for Applied / Closed / Later. Applied sets Applied date."""
    if status not in ACTION_STATUS:
        raise ValueError(f"Action status must be one of {sorted(ACTION_STATUS)}, got {status!r}")
    allowed = allowed_status(board)
    if status not in allowed:
        raise ValueError(f"{status!r} is not valid for {board}")
    P = props_for(board)
    props: dict[str, Any] = {P["status"]: select_prop(status)}
    if status == "Applied":
        props[P["applied_date"]] = date_prop(datetime.now(timezone.utc).date())
    if notes is not None:
        props[P["notes"]] = rich_text(notes)
    if cover_letter is not None:
        props[P["cover_letter"]] = rich_text(cover_letter)
    return props


def build_cv_update(board: Board, cv_path: str) -> dict:
    """Write CV path + Has CV after successful generation."""
    P = props_for(board)
    return {
        P["cv_path"]: rich_text(cv_path),
        P["has_cv"]: checkbox_prop(True),
    }


def build_cover_update(board: Board, cover_path: str) -> dict:
    P = props_for(board)
    return {P["cover_letter"]: rich_text(cover_path)}


def queue_filter() -> dict:
    """Status = Ready."""
    return {
        "property": "Status",
        "select": {"equals": "Ready"},
    }


def needs_cv_filter() -> dict:
    """Has CV unchecked (Build CV queue)."""
    return {
        "property": "Has CV",
        "checkbox": {"equals": False},
    }
