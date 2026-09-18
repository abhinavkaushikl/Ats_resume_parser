#!/usr/bin/env bash
# Start the web UI at http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
exec .venv/bin/uvicorn ats_tailor.web:app --host 127.0.0.1 --port "${PORT:-8000}"
