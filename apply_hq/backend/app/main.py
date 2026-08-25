"""Apply HQ FastAPI — Notion-backed Mik / Spark manual apply surface."""
from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Allow `uvicorn backend.app.main:app` from apply_hq/
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app import config, cv_service, notion_store  # noqa: E402
from backend.app.ai_brain import AIUnavailableError, get_brain  # noqa: E402
from backend.app.schemas import (  # noqa: E402
    BuildCvRequest,
    CoverRequest,
    HealthResponse,
    MarkRequest,
    QueueResponse,
    SessionState,
    StartRequest,
)
from backend.app.session import logs, session  # noqa: E402

config.ensure_dirs()

app = FastAPI(title="Apply HQ", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    brain = get_brain()
    ai_ok, ai_reason = brain.available()
    return HealthResponse(
        ok=True,
        notion=notion_store.notion_configured(),
        ai=ai_ok,
        ai_reason=ai_reason,
        profile=config.profile_ready(),
        mik_ds=config.NOTION_MIK_DATA_SOURCE_ID,
        spark_ds=config.NOTION_SPARK_DATA_SOURCE_ID,
    )


@app.get("/api/queue/{board}", response_model=QueueResponse)
def get_queue(board: str):
    if board not in ("mik", "spark"):
        raise HTTPException(400, "board must be mik or spark")
    try:
        items = notion_store.list_ready(board)  # type: ignore[arg-type]
    except Exception as e:
        logs.emit(f"[Queue] ! {e}", "error")
        raise HTTPException(502, f"Notion query failed: {e}") from e
    logs.emit(f"[Queue] {board}: {len(items)} Ready")
    return QueueResponse(board=board, items=items, count=len(items))  # type: ignore[arg-type]


@app.get("/api/needs-cv/{board}", response_model=QueueResponse)
def get_needs_cv(board: str):
    if board not in ("mik", "spark"):
        raise HTTPException(400, "board must be mik or spark")
    try:
        items = notion_store.list_needs_cv(board)  # type: ignore[arg-type]
    except Exception as e:
        raise HTTPException(502, f"Notion query failed: {e}") from e
    return QueueResponse(board=board, items=items, count=len(items))  # type: ignore[arg-type]


@app.get("/api/session", response_model=SessionState)
def get_session():
    return session.state()


@app.post("/api/session/start", response_model=SessionState)
def start_session(body: StartRequest):
    try:
        return session.start(body.board, body.page_id)
    except Exception as e:
        logs.emit(f"[Apply] ! start failed: {e}", "error")
        raise HTTPException(502, str(e)) from e


@app.post("/api/session/stop", response_model=SessionState)
def stop_session():
    return session.stop()


@app.post("/api/session/next", response_model=SessionState)
def next_job():
    return session.next_job()


@app.post("/api/session/toggle-cover", response_model=SessionState)
def toggle_cover():
    return session.toggle_cover()


@app.post("/api/session/open-link")
def open_link():
    return session.open_link()


@app.post("/api/mark")
def mark(body: MarkRequest):
    try:
        row = notion_store.mark_status(
            body.board, body.page_id, body.status, notes=body.notes
        )
        logs.emit(f"[Mark] {body.status} → {row.get('name')}")
        # Advance session if this was the current row
        cur = session.current()
        if cur and cur.get("page_id") == body.page_id:
            session.next_job()
        return {"ok": True, "row": row, "session": session.state()}
    except Exception as e:
        logs.emit(f"[Mark] ! {e}", "error")
        raise HTTPException(502, str(e)) from e


@app.post("/api/cover-letter")
def cover_letter(body: CoverRequest):
    try:
        row = notion_store.get_page(body.board, body.page_id)
        path = cv_service.generate_cover_letter(
            body.board, row, user_note=body.user_note, log=logs.emit
        )
        refreshed = session.refresh_current() or notion_store.get_page(
            body.board, body.page_id
        )
        return {"ok": True, "path": str(path), "row": refreshed}
    except AIUnavailableError as e:
        logs.emit(f"[Cover] ! {e}", "error")
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        logs.emit(f"[Cover] ! {e}", "error")
        raise HTTPException(502, str(e)) from e


@app.post("/api/build-cv")
def build_cv(body: BuildCvRequest):
    result = cv_service.build_cvs(
        body.board, page_id=body.page_id, limit=body.limit, log=logs.emit
    )
    if not result.get("ok"):
        raise HTTPException(503, result.get("reason") or "CV build unavailable")
    return result


@app.get("/api/logs")
def get_logs():
    return {"entries": logs.snapshot()}


@app.post("/api/logs/clear")
def clear_logs():
    logs.clear()
    return {"ok": True}


@app.get("/api/file")
def get_file(path: str):
    """Serve a local CV / cover PDF for preview (path must be under OUTPUT_DIR)."""
    target = Path(path).expanduser().resolve()
    root = config.OUTPUT_DIR.resolve()
    try:
        target.relative_to(root)
    except ValueError as e:
        raise HTTPException(403, "Path outside output dir") from e
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File not found")
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media or "application/octet-stream")


# Serve built web UI if present (production / one-command mode)
_WEB_DIST = _ROOT / "web" / "dist"
if _WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIST), html=True), name="web")
