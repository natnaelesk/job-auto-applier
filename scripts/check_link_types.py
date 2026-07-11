"""Dev helper: classify what kinds of links the captured posts contain."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import db  # noqa: E402

URL_RE = re.compile(r"https?://\S+")

conn = db.connect()
rows = conn.execute("SELECT id, text FROM messages").fetchall()

only_tme = 0
has_external = 0
has_email = 0
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

for r in rows:
    urls = [u.rstrip(").,]*") for u in URL_RE.findall(r["text"])]
    external = [u for u in urls if "t.me/" not in u]
    if external:
        has_external += 1
    elif urls:
        only_tme += 1
    if EMAIL_RE.search(r["text"]):
        has_email += 1

print(f"total: {len(rows)}")
print(f"has external (non-t.me) link: {has_external}")
print(f"only t.me links: {only_tme}")
print(f"mentions an email: {has_email}")
conn.close()
