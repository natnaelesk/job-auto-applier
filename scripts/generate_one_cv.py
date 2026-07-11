"""Dev helper: generate a single tailored CV (highest-scoring matched job)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import ai  # noqa: E402
import config  # noqa: E402
import cv_generator  # noqa: E402
import db  # noqa: E402

conn = db.connect()
job = conn.execute(
    "SELECT * FROM jobs WHERE status = 'matched' ORDER BY match_score DESC LIMIT 1"
).fetchone()
if not job:
    raise SystemExit("no matched jobs in DB")

print(f"Tailoring CV for: {job['company']} — {job['title']} (score {job['match_score']})")

master = (config.PROFILE_DIR / "master_cv.md").read_text(encoding="utf-8")
prompt = ai.load_prompt(
    "tailor_cv",
    master_cv=master,
    company=job["company"] or "unknown",
    title=job["title"] or "unknown",
    skills=job["skills"] or "[]",
    description=job["description"] or "",
)
cv = ai.ask_json(prompt)
out = config.OUTPUT_DIR / "cvs" / "SAMPLE_real_profile.pdf"
cv_generator._render_pdf(cv, out)
print(f"PDF written: {out} ({out.stat().st_size} bytes)")
conn.close()
