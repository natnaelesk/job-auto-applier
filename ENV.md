# Environment variables

Where secrets and config live for **Job Auto-Applier** (root app) and **Apply HQ**.
Never commit real `.env`, `credentials.json`, `token.json`, Telegram sessions, or filled `profile/*.md`.

Templates: [`.env.example`](.env.example) · [`apply_hq/.env.example`](apply_hq/.env.example)  
Install: [SETUP.md](SETUP.md)

---

## Quick: what to fill first

| Priority | Variable | App | Where to get it |
|----------|----------|-----|-----------------|
| **Required** | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | Root | https://my.telegram.org → API development tools |
| **Required** | `TELEGRAM_CHANNELS` (or `TELEGRAM_CHANNEL`) | Root | Your channel `@usernames` (examples already in `.env.example`) |
| **Required** | `CURSOR_API_KEY` | Root + Apply HQ | https://cursor.com/dashboard → Integrations / API |
| Optional | `NOTION_TOKEN` | Root + Apply HQ | https://www.notion.so/my-integrations |
| Optional | `NOTION_DATABASE_ID` / `NOTION_FOREIGN_DATABASE_ID` | Root | Auto-created on first Notion sync if empty |
| Optional | `NOTION_MIK_DATA_SOURCE_ID` / `NOTION_SPARK_DATA_SOURCE_ID` | Apply HQ | Your Notion collection UUIDs (defaults are Mik/Spark — replace for a personal tracker) |
| Optional | Gmail `credentials.json` | Root | Google Cloud Console → OAuth **Desktop** client → download JSON to project root |

**First useful run (Ethiopia Telegram only):** fill Telegram + `CURSOR_API_KEY`, edit `profile/*.md`, leave Notion/Gmail empty, set `FREEHIRE_ENABLED=false` and `LINKEDIN_ENABLED=false` if you want.

---

## Root app (`.env` in repo root)

Loaded by `src/config.py`.

### Required

| Variable | Notes |
|----------|--------|
| `TELEGRAM_API_ID` | Integer from my.telegram.org |
| `TELEGRAM_API_HASH` | String from my.telegram.org |
| `TELEGRAM_CHANNELS` | Comma list, JSON array, or `t.me` links. Prefer this over legacy `TELEGRAM_CHANNEL`. |
| `CURSOR_API_KEY` | Needed for extract / match / CV / apply AI |

### Optional (sensible defaults in `.env.example`)

| Variable | Default / purpose |
|----------|-------------------|
| `TELEGRAM_CHANNEL` | Legacy single channel if `TELEGRAM_CHANNELS` empty |
| `FIRST_SCAN_DAYS` | `7` — first scan lookback |
| `CURSOR_MODEL` | `composer-2.5` |
| `NOTION_TOKEN` | Notion sync |
| `NOTION_DATABASE_ID` | Ethiopia DB (auto-filled) |
| `NOTION_FOREIGN_DATABASE_ID` | Foreign DB (auto-filled) |
| `FOREIGN_SEARCH_*` / `FREEHIRE_*` / `LINKEDIN_*` | Foreign Search tab |
| `GMAIL_CREDENTIALS_FILE` | Path to OAuth client JSON (default `credentials.json`) |
| `MATCH_THRESHOLD_*` / `APPROVAL_MODE` / `MAX_APPLY_PER_RUN` | Match + apply limits |
| `PLAYWRIGHT_*` / `APPLY_SYSTEM_BROWSER` / `BROWSER_USER_DATA_DIR` | Browser for Apply tab |

Gmail also creates local `token.json` after the first browser login (git-ignored).

---

## Apply HQ (`apply_hq/.env` and/or root `.env`)

Loaded by `apply_hq/backend/app/config.py` — **merges both files**. Non-empty values in `apply_hq/.env` win; empty placeholders do **not** erase parent secrets.

| Variable | Required? | Notes |
|----------|-----------|--------|
| `NOTION_TOKEN` | For live queue | Same token as root is fine |
| `CURSOR_API_KEY` | For Build CV / cover letter | Same key as root is fine |
| `CURSOR_MODEL` | No | Default `composer-2.5` |
| `NOTION_MIK_DATA_SOURCE_ID` | For Mik tab | Default is Mik’s collection — use yours for a personal setup |
| `NOTION_SPARK_DATA_SOURCE_ID` | For Spark tab | Default is Spark’s collection — use yours for a personal setup |
| `PROFILE_DIR` / `OUTPUT_DIR` / `PROMPTS_DIR` | No | Defaults to sibling `../profile`, `../output`, `../prompts` |
| `APPLY_HQ_HOST` / `APPLY_HQ_PORT` / `APPLY_HQ_VITE_PORT` | No | Defaults `127.0.0.1` / `8787` / `5173` |
| `APPLY_HQ_DEMO` | No | UI smoke only when **no** live `NOTION_TOKEN` in either `.env` |

### Frontend

The Vite app under `apply_hq/web/` has **no** `.env` secrets. It proxies `/api` to the FastAPI backend (`vite.config.ts`). Backend env is enough.

---

## Files that must stay local (never git)

| Path | Why |
|------|-----|
| `.env`, `apply_hq/.env` | API keys |
| `credentials.json`, `token.json` | Gmail OAuth |
| `data/*.session*` | Telegram login |
| `profile/about_me.md`, `master_cv.md`, `answers.md` | Your personal profile |
| `data/`, `output/` | DB, sessions, generated CVs |

---

## Cloud Agents

[`.cursor/environment.json`](.cursor/environment.json) installs Python + Apply HQ npm deps on a fresh VM. It does **not** inject secrets — paste keys into local `.env` on your machine after clone.
