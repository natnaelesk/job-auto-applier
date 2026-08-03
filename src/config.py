"""Central configuration: loads .env and defines all paths in one place."""
from pathlib import Path

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROFILE_DIR = PROJECT_ROOT / "profile"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

DB_PATH = DATA_DIR / "jobs.db"
STATE_PATH = DATA_DIR / "state.json"
TELEGRAM_SESSION = str(DATA_DIR / "telegram")

DATA_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "cvs").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "cvs" / "cover_letter").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "cvs" / "general").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "screenshots").mkdir(parents=True, exist_ok=True)

def _env(name: str, default: str = "") -> str:
    """os.getenv with protection against inline-comment artifacts: an empty
    value followed by a comment ('KEY=   # note') must read as empty."""
    value = os.getenv(name, default).strip()
    if value.startswith("#"):
        return default
    return value.split(" #")[0].strip()


# --- Telegram ---
TELEGRAM_API_ID = _env("TELEGRAM_API_ID")
TELEGRAM_API_HASH = _env("TELEGRAM_API_HASH")
# Single channel (legacy) or comma-separated list via TELEGRAM_CHANNELS
TELEGRAM_CHANNEL = _env("TELEGRAM_CHANNEL")
_TELEGRAM_CHANNELS_RAW = _env("TELEGRAM_CHANNELS")


def telegram_channels() -> list[str]:
    """All channels to scan. Prefers TELEGRAM_CHANNELS; falls back to TELEGRAM_CHANNEL."""
    raw = _TELEGRAM_CHANNELS_RAW or TELEGRAM_CHANNEL
    channels: list[str] = []
    for part in raw.replace(";", ",").split(","):
        ch = part.strip()
        if not ch:
            continue
        if ch.startswith("https://t.me/"):
            ch = "@" + ch.rstrip("/").split("/")[-1]
        elif ch.startswith("t.me/"):
            ch = "@" + ch.rstrip("/").split("/")[-1]
        elif not ch.startswith("@"):
            ch = "@" + ch.lstrip("@")
        if ch not in channels:
            channels.append(ch)
    return channels

# --- Cursor SDK ---
CURSOR_API_KEY = _env("CURSOR_API_KEY")
CURSOR_MODEL = _env("CURSOR_MODEL", "composer-2.5")

# --- Notion ---
NOTION_TOKEN = _env("NOTION_TOKEN")
NOTION_DATABASE_ID = _env("NOTION_DATABASE_ID")
# Separate database for foreign / remote-global jobs (auto-created on first sync)
NOTION_FOREIGN_DATABASE_ID = _env("NOTION_FOREIGN_DATABASE_ID")

# --- Foreign job search (freehire + LinkedIn guest) ---
FOREIGN_SEARCH_QUERIES = _env(
    "FOREIGN_SEARCH_QUERIES",
    "backend developer,full stack developer,python developer,react developer",
)
FOREIGN_SEARCH_LOCATION = _env("FOREIGN_SEARCH_LOCATION", "Remote")
FOREIGN_SEARCH_DAYS = int(_env("FOREIGN_SEARCH_DAYS", "14"))
FOREIGN_SEARCH_LIMIT = int(_env("FOREIGN_SEARCH_LIMIT", "20"))
# freehire base URL (swap for self-hosted)
FREEHIRE_API_URL = _env("FREEHIRE_API_URL", "https://freehire.dev").rstrip("/")
# LinkedIn guest: keep volume low (ToS). Max pages per query (10 results/page).
LINKEDIN_MAX_PAGES = int(_env("LINKEDIN_MAX_PAGES", "2"))
LINKEDIN_ENABLED = _env("LINKEDIN_ENABLED", "true").lower() in {"1", "true", "yes"}
FREEHIRE_ENABLED = _env("FREEHIRE_ENABLED", "true").lower() in {"1", "true", "yes"}


def foreign_search_queries() -> list[str]:
    """Comma-separated search queries for foreign job portals."""
    return [q.strip() for q in FOREIGN_SEARCH_QUERIES.split(",") if q.strip()]


# --- Gmail ---
GMAIL_CREDENTIALS_FILE = _env("GMAIL_CREDENTIALS_FILE", "credentials.json")

# --- Behavior ---
# Apply at 50+ so more realistic fits enter the queue (was 70).
MATCH_THRESHOLD_APPLY = int(_env("MATCH_THRESHOLD_APPLY", "50"))
MATCH_THRESHOLD_REVIEW = int(_env("MATCH_THRESHOLD_REVIEW", "35"))
APPROVAL_MODE = _env("APPROVAL_MODE", "confident")  # always | confident | never
PLAYWRIGHT_HEADLESS = _env("PLAYWRIGHT_HEADLESS", "false").lower() in {
    "1",
    "true",
    "yes",
}
# chrome | edge | firefox | chromium
# Default: system Firefox (user's preferred browser).
PLAYWRIGHT_BROWSER = _env("PLAYWRIGHT_BROWSER", "firefox").lower().strip()
if PLAYWRIGHT_BROWSER not in {"chrome", "edge", "firefox", "chromium"}:
    PLAYWRIGHT_BROWSER = "firefox"

# Optional: attach to a real Chrome/Edge you already started (CDP).
# Example: http://127.0.0.1:9222 — scripts/start_real_chrome.ps1
# Ignored when PLAYWRIGHT_BROWSER=firefox.
PLAYWRIGHT_CDP_URL = _env("PLAYWRIGHT_CDP_URL", "")

# Optional overrides
PLAYWRIGHT_EXECUTABLE = _env("PLAYWRIGHT_EXECUTABLE")  # e.g. path to firefox.exe
BROWSER_USER_DATA_DIR = _env("BROWSER_USER_DATA_DIR")  # real/custom profile folder

MAX_APPLY_PER_RUN = int(_env("MAX_APPLY_PER_RUN", "10"))

# true = Open Link uses your real default browser (Firefox accounts stay yours).
# false = Playwright automation window (needed for Form Fill).
APPLY_SYSTEM_BROWSER = _env("APPLY_SYSTEM_BROWSER", "true").lower() in {
    "1",
    "true",
    "yes",
}

# Profile for launched (non-CDP) sessions
_default_profile = DATA_DIR / f"browser_profile_{PLAYWRIGHT_BROWSER}"
BROWSER_PROFILE_DIR = (
    Path(BROWSER_USER_DATA_DIR) if BROWSER_USER_DATA_DIR else _default_profile
)
BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# How far back the very first Telegram scan goes (days)
FIRST_SCAN_DAYS = int(_env("FIRST_SCAN_DAYS", "7"))

# Upload docs for the application agent
DOCS_UPLOAD_DIR = PROFILE_DIR / "docs" / "uploads"
DEGREE_PDF = DOCS_UPLOAD_DIR / "cs_degree.pdf"
GRADES_PDF = DOCS_UPLOAD_DIR / "grade_report.pdf"
ENGLISH_MEDIUM_PDF = DOCS_UPLOAD_DIR / "english_medium_instruction.pdf"
PASSPORT_DATA = PROFILE_DIR / "docs" / "passport_data.md"

def require(name: str, value: str) -> str:
    if not value:
        raise SystemExit(
            f"Missing {name} in .env - copy .env.example to .env and fill it in."
        )
    return value
