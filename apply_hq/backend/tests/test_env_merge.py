"""Env merge: empty apply_hq/.env must not wipe parent secrets / enable demo."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_empty_apply_hq_token_does_not_block_parent(tmp_path, monkeypatch):
    """Reproduce Natnael's Windows layout: DEMO in apply_hq, token in parent."""
    apply_hq = tmp_path / "apply_hq"
    apply_hq.mkdir()
    parent = tmp_path
    (parent / ".env").write_text(
        "NOTION_TOKEN=secret_from_parent\nCURSOR_API_KEY=cursor_key\n",
        encoding="utf-8",
    )
    (apply_hq / ".env").write_text(
        "NOTION_TOKEN=\nAPPLY_HQ_DEMO=1\n",
        encoding="utf-8",
    )

    # Clear secrets so merge is visible
    for key in ("NOTION_TOKEN", "CURSOR_API_KEY", "APPLY_HQ_DEMO"):
        monkeypatch.delenv(key, raising=False)

    import importlib
    import backend.app.config as cfg

    monkeypatch.setattr(cfg, "APPLY_HQ_ROOT", apply_hq)
    monkeypatch.setattr(cfg, "REPO_ROOT", parent)
    cfg._load_merged_dotenv()
    # Re-bind module-level token after reload helper
    monkeypatch.setattr(cfg, "NOTION_TOKEN", cfg._env("NOTION_TOKEN"))
    monkeypatch.setattr(cfg, "CURSOR_API_KEY", cfg._env("CURSOR_API_KEY"))

    assert cfg.live_notion_token() == "secret_from_parent"
    assert os.environ.get("APPLY_HQ_DEMO") == "1"

    from backend.app import demo_store

    assert demo_store.force_enabled() is False
    assert demo_store.demo_flag_ignored_because_token() is True


def test_apply_hq_nonempty_overrides_parent(tmp_path, monkeypatch):
    apply_hq = tmp_path / "apply_hq"
    apply_hq.mkdir()
    parent = tmp_path
    (parent / ".env").write_text("NOTION_TOKEN=parent_token\n", encoding="utf-8")
    (apply_hq / ".env").write_text("NOTION_TOKEN=child_token\n", encoding="utf-8")

    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    import backend.app.config as cfg

    monkeypatch.setattr(cfg, "APPLY_HQ_ROOT", apply_hq)
    monkeypatch.setattr(cfg, "REPO_ROOT", parent)
    cfg._load_merged_dotenv()
    assert cfg._env("NOTION_TOKEN") == "child_token"
