#!/usr/bin/env python3
"""
daily_jobs.py - one simple Markdown file with every AI / ML / data-science job posted in the last 24 hours
in all cities: title, company, location, posting time, link and the full job description.

It checks every company in companies.yaml + jobs/discovered_companies.yaml via their public job feeds,
plus LinkedIn's public job search for every city.
Search-engine discovery runs only if SERPER_API_KEY (or GOOGLE_API_KEY + GOOGLE_CSE_ID) is set, because
the free Bing fallback returns unrelated pages. New companies can be added to companies.yaml by hand or by
the /job-hunt workflow (WORKFLOW.md).

Output
  jobs/daily/jobs_<YYYY-MM-DD>.md

Usage
  .venv/bin/python daily_jobs.py
  .venv/bin/python daily_jobs.py --hours 24 --cities Berlin Munich
  .venv/bin/python daily_jobs.py --min-match 70     # resume match needed to keep a job (default 60, 0 = off)

Every job with a job description is scored against the base resume (job_match.py). Jobs below the
minimum match are left out of the list and named in a short "Skipped" section at the end; jobs without a
description can't be scored and stay in, marked "not scored".
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from job_fetching_agent import ROOT, finder
from job_match import MIN_MATCH
from job_match import score as match_score

load_dotenv(ROOT / ".env")
OUT = ROOT / "jobs"


def jd_text(j) -> str:
    f = OUT / "jd" / finder.jd_filename(j)
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8").split("## Job description", 1)[-1].strip()


def match_jobs(jobs, min_match: int):
    """Score each job's description against the base resume -> (kept, skipped, {job key: Match})."""
    kept, skipped, scores = [], [], {}
    for i, j in enumerate(jobs, 1):
        jd = jd_text(j)
        m = None
        if jd and min_match:
            try:
                m = match_score(jd)
            except Exception as exc:  # LLM down: keep the job, unscored
                print(f"  match not scored ({j.company}): {exc}", flush=True)
        scores[j.key()] = m
        (skipped if m and m.score < min_match else kept).append(j)
        print(f"[match {i}/{len(jobs)}] {f'{m.score}%' if m else 'n/a'} {j.company} - {j.title}", flush=True)
    return kept, skipped, scores


def write_daily(jobs, hours: int, cities: list[str], skipped=(), scores=None, min_match: int = MIN_MATCH):
    """One file, two parts: jobs from company career sites / job boards first, then LinkedIn."""
    scores = scores or {}
    now = datetime.now(timezone.utc)
    path = OUT / "daily" / f"jobs_{datetime.now():%Y-%m-%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs = sorted(jobs, key=lambda j: (cities.index(j.city), -(j.posted or now).timestamp()))
    direct = [j for j in jobs if not finder.is_linkedin(j)]
    linkedin = [j for j in jobs if finder.is_linkedin(j)]
    counts = ", ".join(f"{c} {n}" for c in cities if (n := sum(j.city == c for j in jobs)))
    L = [f"# AI / ML jobs - last {hours}h - {datetime.now():%Y-%m-%d}", "",
         f"{len(jobs)} jobs ({len(direct)} company sites, {len(linkedin)} LinkedIn)"
         + (f" · {counts}" if counts else "") + f" · generated {now:%H:%M} UTC"
         + (f" · {len(skipped)} skipped (resume match below {min_match}%)" if min_match else ""), "",
         "**Jump to:** [Company career sites](#part-1-company-career-sites) · [LinkedIn](#part-2-linkedin)", ""]
    n = 0
    for heading, part in (("# Part 1: Company career sites", direct), ("# Part 2: LinkedIn", linkedin)):
        L += [heading, "", f"{len(part)} jobs", ""]
        if not part:
            L += ["_No matching jobs posted in this window._", ""]
        for j in part:
            n += 1
            posted = f"{j.posted.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC ({finder.age(j.posted)})" if j.posted else "unknown"
            L += ["---", "", f"## {n}. {j.title}", "",
                  f"- **Company:** {j.company}", f"- **Location:** {j.location or j.city}",
                  f"- **Posted:** {posted}", f"- **Visa / relocation:** {finder.visa_cell(j)}",
                  f"- **Link:** {j.url}"]
            m = scores.get(j.key())
            L += ([f"- **Resume match:** {m.score}% - {m.reason}"] if m else
                  ["- **Resume match:** not scored (no job description)"] if min_match else []) + [""]
            jd = jd_text(j)
            L += ["<details><summary>Job description</summary>", "", jd,
                  "", "</details>", ""] if jd else ["_Job description not available - open the link._", ""]
    if skipped:
        L += ["---", "", f"# Skipped - resume match below {min_match}%", ""]
        L += [f"- {scores[j.key()].score}% · {j.company} - {j.title} ({j.city}) · {j.url}" for j in
              sorted(skipped, key=lambda j: -scores[j.key()].score)]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--cities", nargs="*", default=list(finder.CITIES), help="subset of: " + ", ".join(finder.CITIES))
    ap.add_argument("--min-match", type=int, default=MIN_MATCH, help="resume match %% to keep a job (0 = off)")
    a = ap.parse_args()
    if not (os.environ.get("SERPER_API_KEY") or (os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"))):
        finder.discover = lambda *args, **kw: (print("Search discovery skipped (no SERPER_API_KEY); "
                                                     "checking known companies"), [])[1]
    res = finder.run(hours=a.hours, cities=a.cities, out_dir=str(OUT), extra_companies=str(ROOT / "companies.yaml"),
                     linkedin=True)
    kept, skipped, scores = match_jobs(res["jobs"], a.min_match)
    print(f"{len(kept)} kept, {len(skipped)} skipped (resume match < {a.min_match}%)")
    print(f"Daily file: {write_daily(kept, a.hours, a.cities, skipped, scores, a.min_match)}")


if __name__ == "__main__":
    main()
