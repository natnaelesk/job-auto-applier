"""Dev helper: minimal Cursor SDK smoke test with full traceback."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import ai  # noqa: E402  (applies the Windows bridge patch on import)

try:
    print(ai.ask("Reply with exactly the word: pong"))
except Exception:
    traceback.print_exc()
