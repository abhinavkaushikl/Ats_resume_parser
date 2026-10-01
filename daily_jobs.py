#!/usr/bin/env python3
"""
daily_jobs.py - ONE Markdown file with every AI / ML / data-science job posted in the last 24 hours:
company, job, city, posting time and the posting URL. Nothing else.

It checks every company in companies.yaml + jobs/discovered_companies.yaml via their public job feeds,
plus LinkedIn's public job search for every city.
Search-engine discovery runs only if SERPER_API_KEY (or GOOGLE_API_KEY + GOOGLE_CSE_ID) is set, because
the free Bing fallback returns unrelated pages. New companies can be added to companies.yaml by hand or by
the /job-hunt workflow.

No job descriptions are downloaded and nothing is scored - the job descriptions are collected by hand.

Output (the only file written)
  jobs/jobs_<YYYY-MM-DD>.md

The `Visa` column is left empty here; step 2 of /job-hunt (sponsor_registers.py + research) fills it in
this same file with `visa`, `weak` or `unknown`, and moves dropped companies to its bottom section.

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

HEAD = "| Visa | Company | Job | City | Opened | Link |"
RULE = "|---|---|---|---|---|---|"


def write_list(jobs, hours: int, cities: list[str], companies: int) -> "os.PathLike":
    """One file, two parts: jobs from company career sites first, then LinkedIn."""
    now = datetime.now(timezone.utc)
    path = OUT / f"jobs_{datetime.now():%Y-%m-%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    direct = [j for j in jobs if not finder.is_linkedin(j)]
    linkedin = [j for j in jobs if finder.is_linkedin(j)]
    L = [f"# AI / ML / Data Science jobs - last {hours}h - {datetime.now():%Y-%m-%d}", "",
         f"Generated {now:%Y-%m-%d %H:%M} UTC · {len(jobs)} jobs "
         f"({len(direct)} company sites, {len(linkedin)} LinkedIn) · {companies} companies checked", "",
         f"**{len(jobs)} jobs** · _visa tags pending (step 2)_", "",
         "Visa tags (filled by the visa check): `visa` = sponsors · `weak` = weak evidence, confirm with "
         "the recruiter · `unknown` = nothing found. Companies that say no, require existing work rights "
         "or are agencies hiding the employer are listed under *Dropped* at the end.", "",
         "No job descriptions are fetched and nothing is scored here - open the link to read the job.", ""]
    L += _part("# Part 1: Company career sites", direct, cities, now)
    L += _part("# Part 2: LinkedIn", linkedin, cities, now)
    L += ["# Dropped - no sponsorship", "", "_Filled by the visa check._", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def _part(heading, jobs, cities, now) -> list[str]:
    L = [heading, "", f"{len(jobs)} job{'' if len(jobs) == 1 else 's'}", ""]
    if not jobs:
        return L + ["_No matching jobs in this window._", ""]
    for city in cities:
        items = sorted((j for j in jobs if j.city == city), key=lambda j: (j.posted or now), reverse=True)
        if not items:
            continue
        L += [f"## {city} ({len(items)})", "", HEAD, RULE]
        for j in items:
            opened = (f"{j.posted.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC" if j.posted
                      else finder.age(j.posted))
            L.append(f"|  | {finder.esc(j.company)} | [{finder.esc(j.title)}]({j.url}) | {j.city} | "
                     f"{opened} | {j.url} |")
        L.append("")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--cities", nargs="*", default=list(finder.CITIES), help="subset of: " + ", ".join(finder.CITIES))
    a = ap.parse_args()
    if not (os.environ.get("SERPER_API_KEY") or (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"))):
        finder.discover = lambda *args, **kw: (print("Search discovery skipped (no SERPER_API_KEY); "
                                                     "checking known companies"), [])[1]
    # write_files=False: no jobs/jd/ downloads, no second Markdown file, no built-in visa guessing.
    res = finder.run(hours=a.hours, cities=a.cities, out_dir=str(OUT), extra_companies=str(ROOT / "companies.yaml"),
                     linkedin=True, write_files=False)
    jobs = res["jobs"]
    print(f"{len(jobs)} jobs found ({len(res['new_keys'])} new since the last run)")
    print(f"Job list: {write_list(jobs, a.hours, a.cities, res['companies_checked'])}")


if __name__ == "__main__":
    main()
