# Job Auto-Applier

An AI-assisted job pipeline you orchestrate:

1. Scans a Telegram job channel for new postings
2. Scores each job against your profile
3. Generates a tailored CV PDF for each match
4. Syncs everything to Notion
5. **Apply (you drive):** opens links in Chrome; screenshot → AI answers
   (copyable) or Form Fill; you mark Applied / Closed / Later
6. Scans Gmail for company replies and updates the tracker

Built with Python, Playwright, Telethon, the Cursor SDK, and the Notion & Gmail APIs.

**Full architecture and build phases: see [PLAN.md](PLAN.md).**

## Setup

1. Copy profile templates (your real profile stays local / git-ignored):
   ```bash
   cp profile/about_me.example.md profile/about_me.md
   cp profile/master_cv.example.md profile/master_cv.md
   cp profile/answers.example.md profile/answers.md
   ```
   Then fill them with your facts. Optional upload docs: see `profile/docs/README.example.md`.
2. Copy `.env.example` to `.env` and add credentials
3. `pip install -r requirements.txt`
4. (Optional) Real Chrome CDP for Google login:
   `powershell -ExecutionPolicy Bypass -File scripts/start_real_chrome.ps1`
5. (Gmail) Place `credentials.json` in the project root (git-ignored)
6. Run: `python src/main.py ui`

### Useful commands

```bash
python src/main.py ui             # orchestrator only (Gather / Apply / Updates tabs)
python src/main.py apply          # same — opens orchestrator
python src/main.py scan extract match cv notion   # prepare only
python src/main.py gmail          # email replies only
```

### Orchestrator (control panel)

Three tabs:

| Tab | What it does |
|-----|----------------|
| **Gather (1–4)** | Telegram → extract → match → CVs → Notion |
| **Apply (5)** | Open job link → Page / Scroll / **Region** screenshots → **Analyze Form** → copyable answers or **Form Fill** → notes → **Applied / Closed / Later** → Next → Notion each time |
| **Updates (6)** | Gmail scan + Notion |

Apply flow is human-orchestrated: the agent prepares answers and can fill forms when you click **Form Fill**; you submit and mark status.

## Status

- [x] Phase 0 — Scaffold & profile templates
- [x] Phase 1 — Telegram watcher
- [x] Phase 2 — Job matcher
- [x] Phase 3 — CV generator
- [x] Phase 4 — Notion tracker
- [x] Phase 5 — Orchestrated apply (screenshots + AI answers + Form Fill)
- [x] Phase 6 — Gmail scanner
- [ ] Phase 7 — Scheduler
