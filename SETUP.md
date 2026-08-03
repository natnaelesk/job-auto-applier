# Setup guide (fresh clone)

Use this when installing Job Auto-Applier on a **new machine** (for example your own laptop, or a sibling’s).  
Every user must have **their own** `.env`, Telegram login, Notion, Gmail, and `profile/*.md` files. Never copy someone else’s secrets.

## What you need

| Item | Required? | Where to get it |
|------|-----------|-----------------|
| Python 3.11+ | Yes | https://www.python.org/downloads/ (check “Add to PATH”) |
| Cursor account + API key | Yes (for match/CV/AI) | https://cursor.com/dashboard → Integrations / API |
| Telegram API ID + Hash | Yes (Ethiopia Telegram scan) | https://my.telegram.org → API development tools |
| Notion integration | Optional at first | https://www.notion.so/my-integrations |
| Gmail OAuth `credentials.json` | Optional | Google Cloud Console (Desktop OAuth client) |

Free Cursor credit is usually enough for **one light run per day** (few channels, only new posts). Large backfills burn quota fast.

## 1. Clone and install

```powershell
git clone https://github.com/natnaelesk/job-auto-applier.git
cd job-auto-applier
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or run the helper (copies profile templates + `.env`, creates venv, installs deps):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1
```

## 2. Create your profile (required)

```powershell
copy profile\about_me.example.md profile\about_me.md
copy profile\master_cv.example.md profile\master_cv.md
copy profile\answers.example.md profile\answers.md
```

Edit those three files with **your** name, skills, experience, and target roles  
(e.g. medical / health jobs for a non-dev profile). The AI only uses facts you put there.

Optional docs (degree PDF, etc.): see `profile/docs/README.example.md`.

## 3. Create `.env` (required)

```powershell
copy .env.example .env
```

Fill at least:

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_CHANNELS=@your_channel1,@your_channel2
CURSOR_API_KEY=...
```

Leave Notion / Gmail empty until you want them.  
Foreign search (freehire / LinkedIn) can stay off for a med-focused Ethiopia setup:

```env
FREEHIRE_ENABLED=false
LINKEDIN_ENABLED=false
```

## 4. First Telegram login

```powershell
.\.venv\Scripts\python.exe src\main.py scan
```

Telethon will ask for phone number + login code **once**. Session is saved under `data/` (git-ignored).

## 5. Open the app

```powershell
.\.venv\Scripts\python.exe src\main.py ui
```

Or double-click `scripts\launch_ui.bat` (after setup).

### Daily flow (keep it light)

1. **Gather** → Scan → Extract + Match → CVs (+ Notion if configured)  
2. **Apply** → open links, analyze forms, mark Applied / Closed  
3. **Updates** → Gmail (optional)

**Search** tab = foreign/remote job boards (skip if you only want local Telegram).

## 6. Notion (optional)

1. Create an integration, copy the token into `NOTION_TOKEN`  
2. Share a Notion page with that integration  
3. Run Gather / Notion once — it creates the tracker DB and saves the id into `.env`

Use a **separate** Notion database per person. Do not share one tracker.

## 7. Gmail (optional)

1. Google Cloud → OAuth Desktop client → download JSON as `credentials.json` in project root  
2. First Gmail run opens a browser login  
3. `token.json` is created locally (git-ignored)

## Security checklist

- [ ] `.env` is never committed  
- [ ] `profile/about_me.md`, `master_cv.md`, `answers.md` are yours only  
- [ ] No shared Cursor / Telegram / Notion / Gmail between two people  
- [ ] `data/` and `output/` stay on this machine  

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing CURSOR_API_KEY` | Add key to `.env` |
| Telegram phone prompt every time | Don’t delete `data/telegram*.session` |
| Notion “no page shared” | Connect the integration to a page in Notion |
| UI won’t start | Activate `.venv`, run `pip install -r requirements.txt` |
| Quota / rate limits | Fewer channels, once per day, skip foreign search |

## Commands cheat sheet

```powershell
.\.venv\Scripts\python.exe src\main.py ui
.\.venv\Scripts\python.exe src\main.py scan extract match cv notion
.\.venv\Scripts\python.exe src\main.py search-foreign
.\.venv\Scripts\python.exe src\main.py gmail
```
