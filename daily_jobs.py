#!/usr/bin/env python3
"""
daily_jobs.py - one simple Markdown file with every AI / ML / data-science job posted in the last 24 hours
in all cities: title, company, location, posting time, link and the full job description.

It checks every company in companies.yaml + jobs/discovered_companies.yaml via their public job feeds,
plus LinkedIn's public job search for every city.
Search-engine discovery runs only if SERPER_API_KEY (or GOOGLE_API_KEY + GOOGLE_CSE_ID) is set, because
the free Bing fallback returns unrelated pages. New companies can be added to companies.yaml by hand or by
the morning prompt in DAILY_JOBS_PROMPT.md.

Output
  jobs/daily/jobs_<YYYY-MM-DD>.md

Usage
  .venv/bin/python daily_jobs.py
  .venv/bin/python daily_jobs.py --hours 24 --cities Berlin Munich
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from job_fetching_agent import ROOT, finder

load_dotenv(ROOT / ".env")
OUT = ROOT / "jobs"


def jd_text(j) -> str:
    f = OUT / "jd" / finder.jd_filename(j)
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8").split("## Job description", 1)[-1].strip()


def write_daily(jobs, hours: int, cities: list[str]):
    now = datetime.now(timezone.utc)
    path = OUT / "daily" / f"jobs_{datetime.now():%Y-%m-%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs = sorted(jobs, key=lambda j: (cities.index(j.city), -(j.posted or now).timestamp()))
    counts = ", ".join(f"{c} {n}" for c in cities if (n := sum(j.city == c for j in jobs)))
    L = [f"# AI / ML jobs - last {hours}h - {datetime.now():%Y-%m-%d}", "",
         f"{len(jobs)} jobs" + (f" · {counts}" if counts else "") + f" · generated {now:%H:%M} UTC", ""]
    for n, j in enumerate(jobs, 1):
        posted = f"{j.posted.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC ({finder.age(j.posted)})" if j.posted else "unknown"
        L += ["---", "", f"## {n}. {j.title}", "",
              f"- **Company:** {j.company}", f"- **Location:** {j.location or j.city}",
              f"- **Posted:** {posted}", f"- **Link:** {j.url}", ""]
        jd = jd_text(j)
        L += ["<details><summary>Job description</summary>", "", jd,
              "", "</details>", ""] if jd else ["_Job description not available - open the link._", ""]
    if not jobs:
        L += ["_No matching jobs posted in this window._"]
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--cities", nargs="*", default=list(finder.CITIES), help="subset of: " + ", ".join(finder.CITIES))
    a = ap.parse_args()
    if not (os.environ.get("SERPER_API_KEY") or (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"))):
        finder.discover = lambda *args, **kw: (print("Search discovery skipped (no SERPER_API_KEY); "
                                                     "checking known companies"), [])[1]
    res = finder.run(hours=a.hours, cities=a.cities, out_dir=str(OUT), extra_companies=str(ROOT / "companies.yaml"),
                     linkedin=True)
    print(f"Daily file: {write_daily(res['jobs'], a.hours, a.cities)}")


if __name__ == "__main__":
    main()
