#!/usr/bin/env bash
# Fresh clone setup (Linux / macOS / Omarchy)
#
# Creates .venv, installs Python deps, copies profile templates + .env if missing,
# optionally installs Playwright browsers and Apply HQ deps.
#
# Usage:
#   bash scripts/setup_fresh.sh
#   bash scripts/setup_fresh.sh --with-apply-hq
#   bash scripts/setup_fresh.sh --skip-playwright
#   bash scripts/setup_fresh.sh --with-apply-hq --skip-playwright

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WITH_APPLY_HQ=0
SKIP_PLAYWRIGHT=0
for arg in "$@"; do
  case "$arg" in
    --with-apply-hq) WITH_APPLY_HQ=1 ;;
    --skip-playwright) SKIP_PLAYWRIGHT=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Use --with-apply-hq and/or --skip-playwright" >&2
      exit 1
      ;;
  esac
done

echo "==> Job Auto-Applier fresh setup (Linux)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 not found. Install Python 3.11+ (e.g. sudo pacman -S python / apt install python3)." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_OK="$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 11) else 0)')"
if [[ "$PY_OK" != "1" ]]; then
  echo "Python 3.11+ required (found $PY_VER)." >&2
  exit 1
fi

# Tkinter is needed for the CustomTkinter desktop UI (optional for Apply HQ only).
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "WARNING: python3 tkinter missing — desktop UI (src/main.py ui) will fail."
  echo "  Omarchy/Arch:  sudo pacman -S tk"
  echo "  Debian/Ubuntu: sudo apt install python3-tk"
fi

if [[ ! -d .venv ]]; then
  echo "==> Creating .venv"
  python3 -m venv .venv
fi

PY=".venv/bin/python"
PIP=".venv/bin/pip"

echo "==> Installing root requirements"
"$PY" -m pip install --upgrade pip
"$PIP" install -r requirements.txt

if [[ "$SKIP_PLAYWRIGHT" -eq 0 ]]; then
  echo "==> Installing Playwright browsers (firefox + chromium)"
  # --with-deps needs root on some distros; fall back to browsers-only if it fails.
  if ! "$PY" -m playwright install --with-deps firefox chromium 2>/dev/null; then
    echo "    (system deps skipped — installing browser binaries only)"
    "$PY" -m playwright install firefox chromium
  fi
else
  echo "==> Skipping Playwright browsers (--skip-playwright)"
fi

copy_if_missing() {
  local src="$1" dst="$2"
  if [[ -f "$src" && ! -f "$dst" ]]; then
    cp "$src" "$dst"
    echo "==> Created $dst (edit this file)"
  elif [[ -f "$dst" ]]; then
    echo "==> Keep existing $dst"
  fi
}

copy_if_missing "profile/about_me.example.md" "profile/about_me.md"
copy_if_missing "profile/master_cv.example.md" "profile/master_cv.md"
copy_if_missing "profile/answers.example.md" "profile/answers.md"
copy_if_missing ".env.example" ".env"

mkdir -p data output/cvs/general output/cvs/cover_letter output/screenshots profile/docs/uploads

if [[ "$WITH_APPLY_HQ" -eq 1 ]]; then
  echo "==> Apply HQ Python deps"
  "$PIP" install -r apply_hq/requirements.txt
  copy_if_missing "apply_hq/.env.example" "apply_hq/.env"
  if command -v npm >/dev/null 2>&1; then
    echo "==> Apply HQ frontend (npm ci)"
    (cd apply_hq/web && npm ci)
  else
    echo "WARNING: npm not found — install Node.js 20+ for Apply HQ UI."
    echo "  Omarchy/Arch:  sudo pacman -S nodejs npm"
    echo "  Or use nvm / fnm"
  fi
fi

echo ""
echo "Next steps:"
echo "  1. Edit .env                 (TELEGRAM_* and CURSOR_API_KEY — see ENV.md)"
echo "  2. Edit profile/about_me.md, master_cv.md, answers.md"
echo "  3. source .venv/bin/activate"
echo "  4. python src/main.py scan   (Telegram login once)"
echo "  5. python src/main.py ui"
if [[ "$WITH_APPLY_HQ" -eq 1 ]]; then
  echo "  6. Apply HQ: edit apply_hq/.env (or reuse root .env), then:"
  echo "       cd apply_hq && ../.venv/bin/python run.py"
fi
echo ""
echo "Full guide: SETUP.md   |   Secrets map: ENV.md"
