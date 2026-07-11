"""Dev helper: reproduce the SDK's exact bridge spawn to debug discovery."""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cursor_sdk._vendor import resolve_bridge_path  # noqa: E402
from cursor_sdk._bridge import _bridge_subprocess_env  # noqa: E402

argv = [resolve_bridge_path(), "--workspace", str(Path.cwd())]
env = dict(_bridge_subprocess_env())
print("argv[0]:", argv[0])
print("env keys:", len(env))
for key in ("PATH", "SystemRoot", "COMSPEC", "TEMP"):
    print(f"  env has {key}:", key in env)

process = subprocess.Popen(
    argv,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
    env=env,
)
start = time.monotonic()
try:
    for line in process.stderr:
        elapsed = time.monotonic() - start
        print(f"[{elapsed:5.1f}s] STDERR: {line.rstrip()[:200]}")
        if "ready" in line:
            break
        if elapsed > 25:
            break
finally:
    process.kill()
print("exit code:", process.poll())
