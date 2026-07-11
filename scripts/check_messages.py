"""Dev helper: inspect captured messages (link coverage + one sample)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import db  # noqa: E402

conn = db.connect()
total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
with_hidden = conn.execute(
    "SELECT COUNT(*) FROM messages WHERE text LIKE '%[Links in this post]%'"
).fetchone()[0]
with_any_url = conn.execute(
    "SELECT COUNT(*) FROM messages WHERE text LIKE '%http%'"
).fetchone()[0]
print(f"total messages: {total}")
print(f"with hidden (button/entity) links: {with_hidden}")
print(f"with any URL: {with_any_url}")

row = conn.execute("SELECT text FROM messages WHERE id = 5091").fetchone()
if row:
    print("\n--- sample message 5091 ---")
    print(row["text"])
conn.close()
