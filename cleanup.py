#!/usr/bin/env python3
"""
cleanup.py - remove a day's working files once JOB_RESULTS.md is written. Keeps only what you need:
JOB_RESULTS.md, the JD files of the shortlisted jobs (the ones JOB_RESULTS.md links to), the tailored
resumes in applications/, and the state files the next run needs.

Deletes (for --date, default today):
  jobs/jd/, jobs/daily/, jobs/latest.md
  jobs/jobs_<date>_*.md (job list), jobs/research_<date>_sponsors.md, older days' visa files and
  unclear lists (today's are kept for the visa-unsure review),
  jobs/unclear_visa_match_<date>.md, jobs/visa_jobs_<date>.json, jobs/visa_research_<date>.json
  jobs/jd_visa/<date>/skipped/, README.md, SHORTLIST.md, and every other JD file there that
  JOB_RESULTS.md does not link to
  then jobs/jd_visa/<date>/ itself: each shortlisted JD is first MOVED into its application folder
  (applications/<date>/<job>/job_description.md) and JOB_RESULTS.md's links are updated
  outputs/ contents, __pycache__/ folders, .DS_Store files
Never deletes: code, the resume, .env, companies.yaml, applications/, .claude/, JOB_RESULTS.md,
  jobs/seen.json, jobs/discovered_companies.yaml, jobs/visa_companies.json, jobs/registers/

Usage
  .venv/bin/python cleanup.py                     # dry run: list what would be deleted
  .venv/bin/python cleanup.py --yes               # delete
  .venv/bin/python cleanup.py --date 2026-09-25 --yes
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
KEEP = {JOBS / "seen.json", JOBS / "discovered_companies.yaml", JOBS / "visa_companies.json"}
RUNNING = "jd_extractor.py|job_match.py|daily_jobs.py|tailor_all.py|build_resume.py|unclear_visa_match.py"


def size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def targets(date: str) -> list[Path]:
    out = [JOBS / "jd", JOBS / "daily", JOBS / "latest.md",
           # The day's visa file and unclear list are kept for my review of the visa-unsure jobs
           # (jd_extractor.py --only reads them); they go with the next day's cleanup.
           *(f for f in JOBS.glob(f"jobs_{date}_*.md") if not f.name.endswith("_visa.md")),
           *(f for f in [*JOBS.glob("jobs_*_visa.md"), *JOBS.glob("unclear_????-??-??.md")]
             if (m := re.search(r"\d{4}-\d{2}-\d{2}", f.name)) and m.group(0) < date),
           *(JOBS / n for n in (f"research_{date}_sponsors.md", f"unclear_visa_match_{date}.md",
                                f"visa_jobs_{date}.json", f"visa_research_{date}.json", f"register_hits_{date}.json"))]
    day = JOBS / "jd_visa" / date
    if day.exists():
        out += [day / "skipped", day / "README.md", day / "SHORTLIST.md"]
        results = ROOT / "JOB_RESULTS.md"
        text = results.read_text(encoding="utf-8") if results.exists() else ""
        if text.startswith(f"# Job results - {date}"):  # only prune JDs against the same day's results
            linked = set(re.findall(rf"\(jobs/jd_visa/{re.escape(date)}/([^)]+\.md)\)", text))
            out += [f for f in day.glob("*.md") if f.name not in linked | {"README.md", "SHORTLIST.md"}]
    outputs = ROOT / "outputs"
    out += list(outputs.iterdir()) if outputs.exists() else []
    out += [p for p in ROOT.rglob("__pycache__") if ".venv" not in p.parts]
    out += [p for p in ROOT.rglob(".DS_Store") if ".venv" not in p.parts]
    return [p for p in dict.fromkeys(out) if p.exists() and p not in KEEP]


def move_jds(date: str, dry: bool) -> None:
    """Move each shortlisted JD into applications/<date>/<job>/job_description.md and fix the links."""
    day, apps = JOBS / "jd_visa" / date, ROOT / "applications" / date
    results = ROOT / "JOB_RESULTS.md"
    if not day.exists():
        return
    text = results.read_text(encoding="utf-8") if results.exists() else ""
    # skipped/ too: 50-59% visa-confirmed jobs are tailored (tailor-resumes rule) and keep their JD
    for f in sorted([*day.glob("*.md"), *(day / "skipped").glob("*.md")]):
        dest = apps / f.stem
        if not dest.is_dir():
            continue  # no application folder: leave it (deleted below only if JOB_RESULTS doesn't link it)
        print(f"{'move' if not dry else 'would move'}  {f.relative_to(ROOT)} -> {(dest / 'job_description.md').relative_to(ROOT)}")
        if not dry:
            shutil.move(str(f), dest / "job_description.md")
            rel = f.relative_to(day).as_posix()
            text = text.replace(f"(jobs/jd_visa/{date}/{rel})", f"(applications/{date}/{f.stem}/job_description.md)")
    if not dry and text:
        results.write_text(text, encoding="utf-8")
    if not dry and day.exists() and not any(day.iterdir()):
        day.rmdir()
        if not any(day.parent.iterdir()):
            day.parent.rmdir()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=f"{datetime.now():%Y-%m-%d}")
    ap.add_argument("--yes", action="store_true", help="really delete (default: dry run)")
    a = ap.parse_args()

    busy = subprocess.run(["pgrep", "-fl", RUNNING], capture_output=True, text=True).stdout.strip()
    if busy:
        raise SystemExit(f"Not cleaning: a job script is still running:\n{busy}")

    todo = targets(a.date)
    if not todo and not (JOBS / "jd_visa" / a.date).exists():
        print("Nothing to clean.")
        return
    move_jds(a.date, dry=not a.yes)  # first, so JDs of tailored jobs (incl. skipped/) aren't deleted
    total = 0
    for p in todo:
        if not p.exists():  # moved into its application folder above
            continue
        n = size(p)
        total += n
        print(f"{'delete' if a.yes else 'would delete'}  {p.relative_to(ROOT)}{'/' if p.is_dir() else ''}  ({n // 1024} KB)")
        if a.yes:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    print(f"{len(todo)} items, {total // 1024} KB {'deleted' if a.yes else '- dry run, add --yes to delete'}")


if __name__ == "__main__":
    main()
