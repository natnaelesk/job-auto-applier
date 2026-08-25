"""Pydantic schemas for Apply HQ API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Board = Literal["mik", "spark"]
ActionStatus = Literal["Applied", "Closed", "Later"]


class QueueItem(BaseModel):
    board: Board
    page_id: str
    url: str = ""
    name: str = ""
    company: str = ""
    role: str = ""
    status: str | None = None
    apply_link: str | None = None
    source: str | None = None
    location: str | None = None
    remote: bool | None = None
    stack: str = ""
    salary: str | None = None
    why: str = ""
    cv_path: str | None = None
    has_cv: bool = False
    cover_letter: str | None = None
    applied_date: str | None = None
    local_id: Any = None
    notes: str | None = None
    client: str | None = None
    platform: str | None = None
    budget: str | None = None
    package: str | None = None


class QueueResponse(BaseModel):
    board: Board
    items: list[QueueItem]
    count: int


class SessionState(BaseModel):
    board: Board
    active: bool = False
    index: int = 0
    total: int = 0
    current: QueueItem | None = None
    show_cover: bool = False


class StartRequest(BaseModel):
    board: Board
    page_id: str | None = None  # optional resume target


class MarkRequest(BaseModel):
    board: Board
    page_id: str
    status: ActionStatus
    notes: str | None = None


class CoverRequest(BaseModel):
    board: Board
    page_id: str
    user_note: str = ""


class BuildCvRequest(BaseModel):
    board: Board
    page_id: str | None = None  # if set, only that row; else all Has CV unchecked
    limit: int = Field(default=20, ge=1, le=100)


class LogEntry(BaseModel):
    ts: str
    level: str = "info"
    message: str


class HealthResponse(BaseModel):
    ok: bool
    notion: bool
    ai: bool
    ai_reason: str
    profile: bool
    mik_ds: str
    spark_ds: str
