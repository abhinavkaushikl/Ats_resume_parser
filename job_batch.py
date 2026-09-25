#!/usr/bin/env python3
"""
job_batch.py - hourly batch for the Job Fetching Agent's tool: searches ONE location per hour,
so the free Bing search is never hit hard.

Rotation (repeats forever): Berlin -> Paris -> Amsterdam -> every other location in CITIES.
Each run keeps only jobs posted in the last 24 hours.

Output
  jobs/latest.md          all locations combined (each location as of its last search)
  jobs/batch/<City>.md    one file per location
  jobs/batch/state.json   which location is next, so a restart continues the rotation

Usage
  .venv/bin/python job_batch.py            # run forever, one location per hour
  .venv/bin/python job_batch.py --once     # search only the next location, then exit
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from job_fetching_agent import ROOT, finder

load_dotenv(ROOT / ".env")

FIRST = ["Berlin", "Paris", "Amsterdam"]
ORDER = FIRST + [c for c in finder.CITIES if c not in FIRST]
HOURS = 24
OUT = ROOT / "jobs"
BATCH = OUT / "batch"
STATE = BATCH / "state.json"


def save_city(city: str, jobs, new_keys) -> None:
    finder.write_details(jobs, OUT)
    finder.check_visa_relocation(jobs, OUT)            # before saving, so latest.md keeps the marks
    rows = [{**asdict(j), "posted": j.posted.isoformat() if j.posted else None, "new": j.key() in new_keys}
            for j in jobs]
    (BATCH / f"{city}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    finder.write_markdown(jobs, BATCH / f"{city}.md", HOURS, [city], new_keys, {"companies": "-"})


def rebuild_latest(companies: int) -> Path:
    """Combine every location's last result into jobs/latest.md, dropping jobs now older than 24h."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    jobs, new_keys = [], set()
    for city in ORDER:
        f = BATCH / f"{city}.json"
        if not f.exists():
            continue
        for row in json.loads(f.read_text(encoding="utf-8")):
            new = row.pop("new")
            j = finder.Job(**{**row, "posted": finder.parse_date(row["posted"])})
            if j.posted and j.posted < cutoff:
                continue
            jobs.append(j)
            if new:
                new_keys.add(j.key())
    latest = OUT / "latest.md"
    finder.write_markdown(jobs, latest, HOURS, ORDER, new_keys, {"companies": companies})
    return latest


def run_one() -> None:
    state = json.loads(STATE.read_text()) if STATE.exists() else {"next": 0}
    city = ORDER[state["next"] % len(ORDER)]
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] Searching {city} (last {HOURS}h)")
    try:
        res = finder.run(hours=HOURS, cities=[city], out_dir=str(OUT),
                         extra_companies=str(ROOT / "companies.yaml"), write_files=False)
        save_city(city, res["jobs"], res["new_keys"])
        latest = rebuild_latest(res["companies_checked"])
        print(f"  {city}: {len(res['jobs'])} jobs ({len(res['new_keys'])} new) -> {BATCH / (city + '.md')}, {latest}")
    except Exception as ex:                              # one bad hour must not stop the batch
        print(f"  ! {city} failed: {ex}")
    STATE.write_text(json.dumps({"next": (state["next"] + 1) % len(ORDER), "last": city,
                                 "at": datetime.now().isoformat(timespec="seconds")}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="search only the next location, then exit")
    ap.add_argument("--interval", type=int, default=60, help="minutes between locations (default 60)")
    a = ap.parse_args()
    BATCH.mkdir(parents=True, exist_ok=True)
    print("Rotation: " + " -> ".join(ORDER))
    while True:
        start = time.monotonic()
        run_one()
        if a.once:
            return
        wait = max(0, a.interval * 60 - (time.monotonic() - start))
        print(f"  next location in {wait / 60:.0f} min")
        time.sleep(wait)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
