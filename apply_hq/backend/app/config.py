"""Apply HQ configuration — merges apply_hq/.env and repo-root .env.

A live NOTION_TOKEN from either file always wins. Empty placeholders in
apply_hq/.env must not wipe secrets from the parent .env (the Windows
failure mode: APPLY_HQ_DEMO=1 locally + token only in repo-root .env).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

APPLY_HQ_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APPLY_HQ_ROOT.parent


def _clean_env_value(raw: str | None) -> str | None:
    """Return stripped value, or None if missing/comment-only/empty placeholder."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or value.startswith("#"):
        return None
    return value.split(" #")[0].strip() or None


def _load_merged_dotenv() -> None:
    """Merge repo-root .env then apply_hq/.env.

    Rules:
    - Non-empty values from apply_hq/.env override parent.
    - Empty / missing keys in apply_hq/.env do NOT erase parent secrets.
    - Already-set non-empty process env vars are left alone.
    """
    merged: dict[str, str] = {}
    for path in (REPO_ROOT / ".env", APPLY_HQ_ROOT / ".env"):
        if not path.is_file():
            continue
        for key, raw in (dotenv_values(path) or {}).items():
            cleaned = _clean_env_value(raw)
            if cleaned is None:
                # Empty placeholder — keep any value already merged from parent
                continue
            merged[key] = cleaned

    for key, value in merged.items():
        existing = os.environ.get(key)
        if existing is not None and existing.strip():
            continue
        os.environ[key] = value


_load_merged_dotenv()


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    value = value.strip()
    if value.startswith("#"):
        return default
    return value.split(" #")[0].strip()


def _path_env(name: str, default: Path) -> Path:
    raw = _env(name)
    if not raw:
        return default
    p = Path(raw)
    return p if p.is_absolute() else (APPLY_HQ_ROOT / p).resolve()


NOTION_TOKEN = _env("NOTION_TOKEN")
CURSOR_API_KEY = _env("CURSOR_API_KEY")
CURSOR_MODEL = _env("CURSOR_MODEL", "composer-2.5")

# Locked data sources — do not invent columns or use old Job Hunt lists
NOTION_MIK_DATA_SOURCE_ID = _env(
    "NOTION_MIK_DATA_SOURCE_ID", "c7753833-38f9-4885-958f-547e6129a566"
)
NOTION_SPARK_DATA_SOURCE_ID = _env(
    "NOTION_SPARK_DATA_SOURCE_ID", "d6129604-e8be-4995-93db-a7f1b0a07652"
)

PROFILE_DIR = _path_env("PROFILE_DIR", REPO_ROOT / "profile")
OUTPUT_DIR = _path_env("OUTPUT_DIR", REPO_ROOT / "output")
PROMPTS_DIR = _path_env("PROMPTS_DIR", REPO_ROOT / "prompts")

CV_DIR = OUTPUT_DIR / "cvs"
COVER_DIR = CV_DIR / "cover_letter"

HOST = _env("APPLY_HQ_HOST", "127.0.0.1")
PORT = int(_env("APPLY_HQ_PORT", "8787"))


def ensure_dirs() -> None:
    CV_DIR.mkdir(parents=True, exist_ok=True)
    COVER_DIR.mkdir(parents=True, exist_ok=True)


def profile_ready() -> bool:
    """Master CV must exist for tailored generation."""
    return (PROFILE_DIR / "master_cv.md").exists()


def ai_ready() -> tuple[bool, str]:
    """Return (ok, reason). Never fake success when unavailable."""
    if not CURSOR_API_KEY:
        return False, "CURSOR_API_KEY missing — set it in apply_hq/.env or repo-root .env"
    if not profile_ready():
        return False, (
            f"Profile missing — copy profile/master_cv.example.md to "
            f"{PROFILE_DIR / 'master_cv.md'}"
        )
    return True, "ok"


def live_notion_token() -> str:
    """Non-empty NOTION_TOKEN from process env / merged .env files."""
    return (NOTION_TOKEN or "").strip()
