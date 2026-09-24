#!/usr/bin/env bash
# Job Fetching Agent. Results: jobs/latest.md
#   ./run_jobs.sh --batch          # hourly: Berlin -> Paris -> Amsterdam -> others, last 24h (runs until Ctrl+C)
#   ./run_jobs.sh --batch --once   # just the next location in the rotation
#   ./run_jobs.sh "senior AI consultant jobs in London and Oslo, last 3 days"   # one-off agent request
# Search: free Bing by default; set SERPER_API_KEY in .env for faster Google results.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt
if [ "${1:-}" = "--batch" ]; then
  shift
  exec .venv/bin/python -u job_batch.py "$@"
fi
exec .venv/bin/python job_fetching_agent.py "$@"
