"""Demo mode must never hide a live Notion token."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import demo_store  # noqa: E402
from backend.app.cv_service import build_cvs  # noqa: E402
from backend.app.ai_brain import StubAIBrain, AIUnavailableError  # noqa: E402


def test_demo_disabled_when_notion_token_present(monkeypatch):
    monkeypatch.setenv("APPLY_HQ_DEMO", "1")
    with patch("backend.app.config.NOTION_TOKEN", "secret_live_token"):
        assert demo_store.force_enabled() is False
        assert demo_store.demo_flag_ignored_because_token() is True


def test_demo_enabled_only_without_token(monkeypatch):
    monkeypatch.setenv("APPLY_HQ_DEMO", "1")
    with patch("backend.app.config.NOTION_TOKEN", ""):
        assert demo_store.force_enabled() is True


def test_demo_off_by_default(monkeypatch):
    monkeypatch.delenv("APPLY_HQ_DEMO", raising=False)
    with patch("backend.app.config.NOTION_TOKEN", ""):
        assert demo_store.force_enabled() is False


def test_build_cvs_all_failed_returns_ok_false(monkeypatch):
    """WinError-style failures must not return ok:true."""
    rows = [
        {
            "page_id": "p1",
            "name": "Acme — Backend",
            "company": "Acme",
            "role": "Backend",
            "stack": "Python",
            "why": "",
            "notes": "",
            "has_cv": False,
        }
    ]

    class BoomBrain(StubAIBrain):
        def available(self):
            return True, "ok"

        def load_prompt(self, name, **kwargs):
            return "prompt"

        def ask_json(self, prompt):
            raise OSError(10038, "An operation was attempted on something that is not a socket")

    monkeypatch.setattr("backend.app.cv_service.get_brain", lambda: BoomBrain("x"))
    monkeypatch.setattr("backend.app.cv_service.notion_store.list_needs_cv", lambda b: rows)
    monkeypatch.setattr(
        "backend.app.cv_service.config.profile_ready",
        lambda: True,
    )
    # master_cv must exist for generate path — stub generate to raise via brain
    from pathlib import Path
    import backend.app.cv_service as cvs

    master = cvs.config.PROFILE_DIR / "master_cv.md"
    master.parent.mkdir(parents=True, exist_ok=True)
    if not master.exists():
        master.write_text("# master\n", encoding="utf-8")

    result = build_cvs("mik", limit=5)
    assert result["ok"] is False
    assert result["done"] == 0
    assert result["failed"] >= 1
    assert "10038" in result["reason"] or "socket" in result["reason"].lower()


def test_notion_configured_not_lied_by_demo(monkeypatch):
    from backend.app import notion_store

    monkeypatch.setenv("APPLY_HQ_DEMO", "1")
    with patch("backend.app.config.NOTION_TOKEN", ""):
        assert demo_store.force_enabled() is True
        assert notion_store.notion_configured() is False
