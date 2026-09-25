#!/usr/bin/env python3
"""
tailor_all.py - tailored resume + cover letter for every shortlisted job of the day, in one batch.

Takes every job-description file in jobs/jd_visa/<date>/ (the 60%+ matches, visa-confirmed and
visa-unclear; not skipped/) and runs the same tailoring pipeline as the web UI on each (ats_tailor,
TAILOR_MODE from .env - "subtle" by default: title, summary and one new project change, the rest of the
resume stays as it is), including the HR / ATS judge. Jobs already done are skipped, so it can be re-run.

Output
  applications/<date>/<Company>_<Title>_<City>/   resume PDF (.tex if no LaTeX engine), cover letter,
                                                  project_brief.md, job_description.txt, report.json
  applications/<date>/index.json                  per job: files + judge score (read by job_report.py)

Usage
  .venv/bin/python tailor_all.py                          # today
  .venv/bin/python tailor_all.py --date 2026-09-25
  .venv/bin/python tailor_all.py --limit 3                # quick test
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from ats_tailor.config import get_settings
from ats_tailor.pipeline import TailoringPipeline, job_dir

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
APPS = ROOT / "applications"


def header(text: str, key: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(key)}:\*\* (.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=f"{datetime.now():%Y-%m-%d}")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)-7s %(message)s")

    jd_dir = JOBS / "jd_visa" / a.date
    files = sorted(f for f in jd_dir.glob("*.md") if f.name not in ("README.md", "SHORTLIST.md"))[: a.limit or None]
    out_root = APPS / a.date
    out_root.mkdir(parents=True, exist_ok=True)
    index_file = out_root / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else {}
    settings = get_settings()
    pipeline = TailoringPipeline(settings)
    print(f"{len(files)} shortlisted jobs in {jd_dir} -> {out_root} (mode: {settings.tailor_mode})", flush=True)

    for i, f in enumerate(files, 1):
        if f.stem in index and (out_root / f.stem).exists():
            print(f"[{i}/{len(files)}] done already  {f.stem}", flush=True)
            continue
        text = f.read_text(encoding="utf-8")
        jd = text.split("## Job description", 1)[-1].strip()
        company, city = header(text, "Company"), header(text, "City")
        started = time.time()
        try:
            result = pipeline.run(jd, company=company or None, city=city or None)
        except Exception as exc:  # one bad job must not stop the batch
            print(f"[{i}/{len(files)}] FAILED  {f.stem}: {exc}", flush=True)
            continue
        dest = out_root / f.stem
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(job_dir(settings, result.job_id)), dest)
        pdf = result.files.get("resume_pdf")
        index[f.stem] = dict(
            company=company, city=city, role=result.role, hr_score=result.hr_score,
            resume=f"{dest.name}/{pdf or result.files['resume_tex']}",
            cover_letter=f"{dest.name}/{result.files.get('cover_letter_pdf') or result.files['cover_letter_tex']}",
            project_brief=f"{dest.name}/project_brief.md" if "project_brief" in result.files else None,
            warnings=result.warnings, seconds=round(time.time() - started))
        index_file.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"[{i}/{len(files)}] judge {result.hr_score if result.hr_score is not None else '-'}/100  "
              f"{f.stem}  ({index[f.stem]['seconds']}s{', no PDF' if not pdf else ''})", flush=True)

    done = sum(1 for f in files if f.stem in index)
    print(f"{done}/{len(files)} tailored -> {out_root}", flush=True)


if __name__ == "__main__":
    main()
