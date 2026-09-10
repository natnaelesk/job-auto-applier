#!/usr/bin/env bash
# Launch the CustomTkinter desktop UI (Linux / macOS).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "No .venv found. Run: bash scripts/setup_fresh.sh" >&2
  exit 1
fi
exec .venv/bin/python src/main.py ui "$@"
