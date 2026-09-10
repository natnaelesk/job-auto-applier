# Setup guide (fresh clone)

Use this when installing Job Auto-Applier on a **new machine** (Linux, Windows, or a Cursor Cloud Agent VM).  
Every user must have **their own** `.env`, Telegram login, Notion, Gmail, and `profile/*.md` files. Never copy someone else’s secrets.

**Secrets map (what to fill + where to get keys):** **[ENV.md](ENV.md)**

## What you need

| Item | Required? | Where to get it |
|------|-----------|-----------------|
| Python 3.11+ | Yes | https://www.python.org/downloads/ — or distro packages (see Linux below) |
| Cursor account + API key | Yes (for match/CV/AI) | https://cursor.com/dashboard → Integrations / API |
| Telegram API ID + Hash | Yes (Ethiopia Telegram scan) | https://my.telegram.org → API development tools |
| Notion integration | Optional at first | https://www.notion.so/my-integrations |
| Gmail OAuth `credentials.json` | Optional | Google Cloud Console (Desktop OAuth client) |
| Node.js 20+ + npm | Only for Apply HQ UI | Distro package, nvm, or https://nodejs.org |

Free Cursor credit is usually enough for **one light run per day** (few channels, only new posts). Large backfills burn quota fast.

---

## 1. Clone and install

### Linux (Omarchy / Arch / Debian / Ubuntu)

```bash
git clone https://github.com/natnaelesk/job-auto-applier.git
cd job-auto-applier
bash scripts/setup_fresh.sh
```

System packages you may need once:

| Distro | Packages |
|--------|----------|
| Omarchy / Arch | `sudo pacman -S python python-pip tk` — plus `nodejs npm` if using Apply HQ |
| Debian / Ubuntu | `sudo apt install python3 python3-venv python3-pip python3-tk` — plus `nodejs npm` if using Apply HQ |

Apply HQ (Notion apply surface) in the same venv:

```bash
bash scripts/setup_fresh.sh --with-apply-hq
```

Skip browser download (faster; install later with `playwright install`):

```bash
bash scripts/setup_fresh.sh --skip-playwright
```

Manual equivalent:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install firefox chromium   # optional until you use Apply form-fill
cp .env.example .env
cp profile/about_me.example.md profile/about_me.md
cp profile/master_cv.example.md profile/master_cv.md
cp profile/answers.example.md profile/answers.md
```

### Windows

```powershell
git clone https://github.com/natnaelesk/job-auto-applier.git
cd job-auto-applier
powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1
```

Optional: `-WithApplyHq` · `-SkipPlaywright`

Or manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Create your profile (required)

The setup scripts copy templates if missing. Otherwise:

```bash
# Linux / macOS
cp profile/about_me.example.md profile/about_me.md
cp profile/master_cv.example.md profile/master_cv.md
cp profile/answers.example.md profile/answers.md
```

```powershell
# Windows
copy profile\about_me.example.md profile\about_me.md
copy profile\master_cv.example.md profile\master_cv.md
copy profile\answers.example.md profile\answers.md
```

Edit those three files with **your** name, skills, experience, and target roles. The AI only uses facts you put there.

Optional docs (degree PDF, etc.): see `profile/docs/README.example.md`.

---

## 3. Create `.env` (required)

```bash
cp .env.example .env          # Linux / macOS
# copy .env.example .env      # Windows
```

Fill at least (details in [ENV.md](ENV.md)):

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
CURSOR_API_KEY=...
```

**Telegram channels** = a list of `@usernames` in `.env` (comma-separated or JSON array).  
`.env.example` already has sample Ethiopia tech channels — replace with yours:

```env
# Comma list (easiest):
TELEGRAM_CHANNELS=@josad_software,@freelance_ethio,@hahujobs,@Maroset,@AbiLink7

# Or JSON array:
# TELEGRAM_CHANNELS=["@channel_one","@channel_two"]
```

To add a channel: open it in Telegram → copy the username after `t.me/` → add `@that_name` to the list.

Leave Notion / Gmail empty until you want them.  
Foreign search (freehire / LinkedIn) can stay off for a med-focused Ethiopia setup:

```env
FREEHIRE_ENABLED=false
LINKEDIN_ENABLED=false
```

---

## 4. First Telegram login

```bash
# Linux / macOS
source .venv/bin/activate
python src/main.py scan
```

```powershell
# Windows
.\.venv\Scripts\python.exe src\main.py scan
```

Telethon will ask for phone number + login code **once**. Session is saved under `data/` (git-ignored).

---

## 5. Open the app

```bash
# Linux / macOS
python src/main.py ui
# or: bash scripts/launch_ui.sh
```

```powershell
# Windows
.\.venv\Scripts\python.exe src\main.py ui
# or: scripts\launch_ui.bat
```

### Daily flow (keep it light)

1. **Gather** → Scan → Extract + Match → CVs (+ Notion if configured)  
2. **Apply** → open links, analyze forms, mark Applied / Closed  
3. **Updates** → Gmail (optional)

**Search** tab = foreign/remote job boards (skip if you only want local Telegram).

---

## 6. Apply HQ (optional)

Separate Notion-driven apply UI (Mik / Spark or your own data sources). See [`apply_hq/README.md`](apply_hq/README.md).

```bash
bash scripts/setup_fresh.sh --with-apply-hq
# edit apply_hq/.env (or reuse root .env secrets)
cd apply_hq && ../.venv/bin/python run.py
```

UI: http://127.0.0.1:5173 · API: http://127.0.0.1:8787

---

## 7. Notion (optional)

1. Create an integration, copy the token into `NOTION_TOKEN`  
2. Share a Notion page with that integration  
3. Run Gather / Notion once — it creates the tracker DB and saves the id into `.env`

Use a **separate** Notion database per person. Do not share one tracker.

---

## 8. Gmail (optional)

1. Google Cloud → OAuth Desktop client → download JSON as `credentials.json` in project root  
2. First Gmail run opens a browser login  
3. `token.json` is created locally (git-ignored)

---

## Cursor Cloud Agents

This repo includes [`.cursor/environment.json`](.cursor/environment.json) so a fresh cloud VM can `pip install` root + Apply HQ deps and `npm ci` the frontend. It does **not** create secrets — paste Telegram / Cursor / Notion / Gmail credentials into local `.env` on your machine (see [ENV.md](ENV.md)).

---

## Security checklist

- [ ] `.env` / `apply_hq/.env` are never committed  
- [ ] `profile/about_me.md`, `master_cv.md`, `answers.md` are yours only  
- [ ] No shared Cursor / Telegram / Notion / Gmail between two people  
- [ ] `data/` and `output/` stay on this machine  

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing CURSOR_API_KEY` | Add key to `.env` — see [ENV.md](ENV.md) |
| Telegram phone prompt every time | Don’t delete `data/telegram*.session` |
| Notion “no page shared” | Connect the integration to a page in Notion |
| UI won’t start / `tkinter` | Activate `.venv`; install `python3-tk` / Arch `tk`; `pip install -r requirements.txt` |
| Playwright browser missing | `source .venv/bin/activate && python -m playwright install firefox chromium` |
| Quota / rate limits | Fewer channels, once per day, skip foreign search |

---

## Commands cheat sheet

```bash
# Linux / macOS (venv activated)
python src/main.py ui
python src/main.py scan extract match cv notion
python src/main.py search-foreign
python src/main.py gmail
```

```powershell
# Windows
.\.venv\Scripts\python.exe src\main.py ui
.\.venv\Scripts\python.exe src\main.py scan extract match cv notion
.\.venv\Scripts\python.exe src\main.py search-foreign
.\.venv\Scripts\python.exe src\main.py gmail
```
