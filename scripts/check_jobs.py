"""Dev helper: summarize extracted jobs quality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import db  # noqa: E402

conn = db.connect()
total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
print(f"total jobs: {total}")

for col in ("company", "title", "link", "location", "salary", "experience"):
    filled = conn.execute(
        f"SELECT COUNT(*) FROM jobs WHERE {col} IS NOT NULL AND {col} != ''"
    ).fetchone()[0]
    print(f"  {col:12s} filled: {filled}/{total}")

print("\napply methods:")
for row in conn.execute(
    "SELECT apply_method, COUNT(*) AS n FROM jobs GROUP BY apply_method ORDER BY n DESC"
):
    print(f"  {row['apply_method']}: {row['n']}")

print("\nsample of 10 jobs:")
for row in conn.execute(
    "SELECT company, title, location, apply_method, SUBSTR(link, 1, 60) AS link FROM jobs LIMIT 10"
):
    print(f"  [{row['apply_method']:8s}] {str(row['company'])[:25]:25s} | "
          f"{str(row['title'])[:35]:35s} | {str(row['location'])[:20]:20s} | {row['link']}")
conn.close()
