"""Dev helper: one-time conversion of Match Reasons from multi_select to rich_text."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config  # noqa: E402
import notion_tracker  # noqa: E402

notion = notion_tracker._client()
notion.request(
    path=f"databases/{config.NOTION_DATABASE_ID}",
    method="PATCH",
    body={"properties": {"Match Reasons": {"rich_text": {}}}},
)
print("Match Reasons property converted to rich_text.")
