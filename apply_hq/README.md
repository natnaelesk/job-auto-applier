# Apply HQ

Human-driven desktop apply surface for **Mik** (employment) and **Spark** (freelance).
Notion is the queue. You control every submit — no auto-apply, no Telegram, no hunt UI.

## One command

```bash
cd apply_hq
cp .env.example .env   # once — fill secrets
python run.py
```

Opens:

- UI: http://127.0.0.1:5173
- API: http://127.0.0.1:8787

## Secrets (`.env`)

| Key | Purpose |
|-----|---------|
| `NOTION_TOKEN` | Notion integration token |
| `CURSOR_API_KEY` | Cursor SDK for CV / cover letter |
| `NOTION_MIK_DATA_SOURCE_ID` | `c7753833-38f9-4885-958f-547e6129a566` |
| `NOTION_SPARK_DATA_SOURCE_ID` | `d6129604-e8be-4995-93db-a7f1b0a07652` |

Also needs a local profile: `../profile/master_cv.md` (copy from `master_cv.example.md`).
If the key or profile is missing, CV/cover endpoints return **503** with a clear error — they do not fake success.

## UI

Exactly two tabs: **Mik** and **Spark**.

1. **Top** — queue table (`Status = Ready`)
2. **Front** — only **Start applying** and **Build CV**
3. **Below** — logs

While applying: open/copy job link, create cover letter, copy CV path, preview CV PDF, toggle cover letter, mark **Applied / Closed / Later**.

## Notion (locked)

Do not invent columns. Do not use old Job Hunt lists.

**Mik Jobs** — queue = Ready; Build CV = Has CV unchecked. Actions write Status + Applied date (on Applied); may write Cover letter. CV build writes CV path + Has CV.

**Spark Projects** — same buttons / flow.

CVs land at `../output/cvs/CV_<Name>_<Company>.pdf` (same naming as the existing generator).

## Smoke test

```bash
cd apply_hq
pip install -r requirements.txt pytest
PYTHONPATH=. pytest backend/tests/test_property_mapping.py -q
```

## Layout

```
apply_hq/
  run.py              # one command
  .env.example
  requirements.txt
  backend/app/        # FastAPI + Notion + PDF + AI stub interface
  backend/tests/      # property mapping smoke tests
  web/                # Vite + React + Tailwind
```

Sibling to the existing CustomTkinter app — does not replace or restyle it.
