"""Apply HQ configuration — loads .env from apply_hq/ then repo root."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APPLY_HQ_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APPLY_HQ_ROOT.parent

# Prefer apply_hq/.env, fall back to repo-root .env
load_dotenv(APPLY_HQ_ROOT / ".env")
load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
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
        return False, "CURSOR_API_KEY missing — set it in apply_hq/.env"
    if not profile_ready():
        return False, (
            f"Profile missing — copy profile/master_cv.example.md to "
            f"{PROFILE_DIR / 'master_cv.md'}"
        )
    return True, "ok"
