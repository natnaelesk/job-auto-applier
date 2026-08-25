"""Notion data-source client for Mik Jobs + Spark Projects.

Uses locked data source IDs. Never invents columns.
Demo fixtures only when APPLY_HQ_DEMO=1 AND no NOTION_TOKEN.
"""
from __future__ import annotations

from typing import Any

from notion_client import Client

from . import config, demo_store
from .mapping import (
    Board,
    build_cover_update,
    build_cv_update,
    build_status_update,
    needs_cv_filter,
    parse_page,
    queue_filter,
)


def _client() -> Client:
    token = config.NOTION_TOKEN
    if not token:
        raise RuntimeError("NOTION_TOKEN missing — set it in apply_hq/.env")
    return Client(auth=token)


def data_source_id(board: Board) -> str:
    if board == "mik":
        ds = config.NOTION_MIK_DATA_SOURCE_ID
    else:
        ds = config.NOTION_SPARK_DATA_SOURCE_ID
    if ds.startswith("collection://"):
        ds = ds.split("://", 1)[1]
    return ds.strip()


def query_pages(
    board: Board,
    *,
    filter_obj: dict | None = None,
    page_size: int = 100,
) -> list[dict]:
    notion = _client()
    ds = data_source_id(board)
    results: list[dict] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter_obj:
            body["filter"] = filter_obj
        if cursor:
            body["start_cursor"] = cursor
        resp = notion.data_sources.query(data_source_id=ds, **body)
        batch = resp.get("results") or []
        results.extend(batch)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        if not cursor:
            break
    return results


def list_ready(board: Board) -> list[dict]:
    """Queue = Status Ready. Live Notion when token present."""
    if demo_store.force_enabled():
        return demo_store.list_ready(board)
    pages = query_pages(board, filter_obj=queue_filter())
    return [parse_page(board, p) for p in pages]


def list_needs_cv(board: Board) -> list[dict]:
    """Build CV = Has CV unchecked."""
    if demo_store.force_enabled():
        return demo_store.list_needs_cv(board)
    pages = query_pages(board, filter_obj=needs_cv_filter())
    return [parse_page(board, p) for p in pages]


def get_page(board: Board, page_id: str) -> dict:
    if demo_store.force_enabled():
        return demo_store.get_page(board, page_id)
    notion = _client()
    page = notion.pages.retrieve(page_id=page_id)
    return parse_page(board, page)


def update_properties(page_id: str, properties: dict) -> None:
    if demo_store.force_enabled():
        raise RuntimeError("Demo mode — refusing Notion write")
    notion = _client()
    notion.pages.update(page_id=page_id, properties=properties)


def mark_status(
    board: Board,
    page_id: str,
    status: str,
    *,
    notes: str | None = None,
    cover_letter: str | None = None,
) -> dict:
    build_status_update(board, status, notes=notes, cover_letter=cover_letter)
    if demo_store.force_enabled():
        return demo_store.mark_status(board, page_id, status, notes=notes)
    props = build_status_update(
        board, status, notes=notes, cover_letter=cover_letter
    )
    update_properties(page_id, props)
    return get_page(board, page_id)


def write_cv(board: Board, page_id: str, cv_path: str) -> dict:
    if demo_store.force_enabled():
        return demo_store.write_cv(board, page_id, cv_path)
    update_properties(page_id, build_cv_update(board, cv_path))
    return get_page(board, page_id)


def write_cover(board: Board, page_id: str, cover_path: str) -> dict:
    if demo_store.force_enabled():
        return demo_store.write_cover(board, page_id, cover_path)
    update_properties(page_id, build_cover_update(board, cover_path))
    return get_page(board, page_id)


def notion_configured() -> bool:
    """True only when a live NOTION_TOKEN is set — never lied about by demo."""
    return bool(
        (config.NOTION_TOKEN or "").strip()
        and data_source_id("mik")
        and data_source_id("spark")
    )
