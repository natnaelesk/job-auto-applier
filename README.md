# Job Auto-Applier

AI-assisted job pipeline you run locally:

1. Scan Telegram job channels (and optionally foreign boards: freehire / LinkedIn guest)
2. Score jobs against **your** profile
3. Generate tailored CV PDFs
4. Sync to Notion (optional; SQLite is source of truth)
5. **Apply tab (you drive):** open links, screenshot → AI answers, mark Applied / Closed
6. Scan Gmail for replies (optional)

Stack: Python, Telethon, Cursor SDK, Playwright, Notion API, Gmail API, CustomTkinter.

**Architecture notes:** [PLAN.md](PLAN.md)  
**Install from a fresh clone:** **[SETUP.md](SETUP.md)** ← start here

---

## Quick start (Windows)

```powershell
git clone https://github.com/natnaelesk/job-auto-applier.git
cd job-auto-applier
powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1
```

Then:

1. Edit `.env` — Telegram API + `CURSOR_API_KEY`
2. Edit `profile/about_me.md`, `master_cv.md`, `answers.md`
3. `.\.venv\Scripts\python.exe src\main.py scan`  (Telegram login once)
4. `.\.venv\Scripts\python.exe src\main.py ui`

Or: `scripts\launch_ui.bat`

---

## What is / is not in GitHub

| In the repo (safe to clone) | Local only (never committed) |
|-----------------------------|------------------------------|
| Source code, prompts, UI | `.env` (API keys) |
| `profile/*.example.md` templates | `profile/about_me.md`, `master_cv.md`, `answers.md` |
| `.env.example` | `credentials.json`, `token.json` |
| Setup scripts | `data/` (DB, Telegram session) |
| | `output/` (generated CVs) |

Each person who clones must create **their own** credentials and profile.

---

## App tabs

| Tab | Purpose |
|-----|---------|
| **General** | Dashboard + run agents |
| **Gather** | Telegram → extract → match → CVs → Notion |
| **Search** | Foreign search (freehire / LinkedIn) — optional |
| **Apply** | Human apply queue (Ethiopia / Foreign / All) |
| **Updates** | Gmail replies |

---

## Useful commands

```powershell
.\.venv\Scripts\python.exe src\main.py ui
.\.venv\Scripts\python.exe src\main.py scan extract match cv notion
.\.venv\Scripts\python.exe src\main.py search-foreign
.\.venv\Scripts\python.exe src\main.py gmail
.\.venv\Scripts\python.exe src\main.py notion-full
```

---

## Sharing with someone else (e.g. family)

1. They clone this repo on **their** PC  
2. Run `scripts/setup_fresh.ps1`  
3. Use **their** Telegram + Cursor key + Notion  
4. Fill profile for **their** field (dev, medical, etc.)  
5. Do **not** send them your `.env` or real profile files  

Details: [SETUP.md](SETUP.md)

---

## Status

- [x] Telegram watcher + multi-channel
- [x] Match + CV + Notion (Ethiopia + Foreign DBs)
- [x] Foreign sources (freehire, LinkedIn guest)
- [x] Orchestrated Apply UI
- [x] Gmail scanner
- [ ] Scheduler (optional)
