"""One-command launcher for Apply HQ.

Dev: starts FastAPI + Vite together.
Prod-ish: builds web once, then serves API + static from one process.

Usage (from apply_hq/):
  python run.py
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
WEB = ROOT / "web"
HOST = os.environ.get("APPLY_HQ_HOST", "127.0.0.1")
PORT = os.environ.get("APPLY_HQ_PORT", "8787")
VITE_PORT = os.environ.get("APPLY_HQ_VITE_PORT", "5173")


def _ensure_python_deps() -> None:
    req = ROOT / "requirements.txt"
    print("[apply_hq] Ensuring Python deps…")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
    )


def _ensure_node_deps() -> None:
    if not (WEB / "node_modules").exists():
        print("[apply_hq] npm install…")
        subprocess.check_call(["npm", "install"], cwd=str(WEB))


def _env() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def main() -> int:
    if not (ROOT / ".env").exists() and not (ROOT.parent / ".env").exists():
        print(
            "[apply_hq] No .env found. Copy apply_hq/.env.example → apply_hq/.env "
            "and fill NOTION_TOKEN / CURSOR_API_KEY / data source ids."
        )

    _ensure_python_deps()
    _ensure_node_deps()

    procs: list[subprocess.Popen] = []

    def shutdown(*_args):
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--reload",
    ]
    print(f"[apply_hq] API  http://{HOST}:{PORT}")
    procs.append(subprocess.Popen(api_cmd, cwd=str(ROOT), env=_env()))

    # Wait briefly so Vite proxy target is up
    time.sleep(1.2)

    vite = shutil.which("npm")
    if not vite:
        print("[apply_hq] npm not found — API only. Open http://%s:%s/docs" % (HOST, PORT))
        return procs[0].wait()

    print(f"[apply_hq] UI   http://{HOST}:{VITE_PORT}")
    procs.append(
        subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", HOST, "--port", str(VITE_PORT)],
            cwd=str(WEB),
            env=_env(),
        )
    )

    print("[apply_hq] Ready — open the UI URL. Ctrl+C to stop.")
    # Wait on either process
    while True:
        for p in procs:
            code = p.poll()
            if code is not None:
                shutdown()
                return code or 0
        time.sleep(0.4)


if __name__ == "__main__":
    raise SystemExit(main())
