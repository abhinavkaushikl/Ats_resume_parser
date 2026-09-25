#!/usr/bin/env python3
"""
visa_jobs_json.py - one JSON file with every visa-sponsoring job of the day: the jobs kept by the visa
check (jobs/*_visa.md) plus the removed jobs whose company the deeper research found to sponsor
(jobs/visa_research_<date>.json, verdict yes / weak).

Each job has its visa verdict and source, the full job description when one was extracted (company site, else LinkedIn public page)
(jobs/jd_visa/<date>/, or the company-site JD in jobs/jd/), and the resume match when it was scored.
Jobs without an extracted description are kept with "description": null.

Output
  jobs/visa_jobs_<date>.json

Usage
  .venv/bin/python visa_jobs_json.py                                   # newest jobs/*_visa.md
  .venv/bin/python visa_jobs_json.py jobs/jobs_2026-09-25_0014_visa.md
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from jd_extractor import parse_visa_file, slug
from job_match import MIN_MATCH, cached

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"


def header(text: str, key: str) -> str | None:
    m = re.search(rf"^- \*\*{re.escape(key)}:\*\* (.+)$", text, re.M)
    return m.group(1).strip() if m else None


def source_rows(src_file: Path) -> dict[str, dict]:
    """Job URL -> {city, company, title, jd file} from the source job table."""
    rows, city = {}, None
    for line in src_file.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## (\w+) \(", line):
            city = m.group(1)
        if line.startswith("| ") and "](" in line:
            cells = [x.strip() for x in line.split(" | ")]
            t = re.search(r"\[(.*?)\]\((.*?)\)", cells[1])
            jd = re.search(r"\[JD\]\((.*?)\)", line)
            if t:
                rows[t.group(2)] = dict(city=city, company=cells[2], title=t.group(1),
                                        jd=JOBS / jd.group(1) if jd else None)
    return rows


def _split(s: str) -> list[str]:
    return [x.strip() for x in s.split("; " if "; " in s else ", ") if x.strip()]


def match(body: str, text: str) -> dict | None:
    """The saved resume match for this JD (full, from the score cache), else what the JD file header says."""
    if m := cached(body):
        return dict(score=m.score, status="shortlisted" if m.score >= MIN_MATCH else "skipped", reason=m.reason,
                    matched=m.matched, missing=m.missing, blockers=m.blockers)
    h = re.match(r"(\d+)% - (\w+): (.*)", header(text, "Resume match") or "")
    if not h:
        return None
    return dict(score=int(h.group(1)), status=h.group(2), reason=h.group(3),
                matched=_split(header(text, "Matched") or ""), missing=_split(header(text, "Missing") or ""),
                blockers=_split(header(text, "Blockers") or ""))


def description(city: str, company: str, title: str, url: str, jd_dir: Path, jd_file: Path | None) -> dict:
    """Extracted JD (never from LinkedIn) and its resume match, or nulls."""
    name = f"{slug(company)}_{slug(title)}_{city}.md"
    for f in (jd_dir / name, jd_dir / "skipped" / name):
        if f.exists():
            text = f.read_text(encoding="utf-8")
            body = text.split("## Job description", 1)[-1].strip()
            return dict(description=body, description_source=header(text, "JD source (Playwright)"),
                        resume_match=match(body, text))
    if jd_file and jd_file.exists() and "linkedin." not in url:  # company-site job: its feed JD is not LinkedIn
        body = jd_file.read_text(encoding="utf-8").split("## Job description", 1)[-1].strip()
        return dict(description=body, description_source=url, resume_match=match(body, ""))
    return dict(description=None, description_source=None, resume_match=None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("visa_file", nargs="?", type=Path, help="jobs/*_visa.md (default: newest)")
    a = ap.parse_args()
    visa_file = a.visa_file or max(JOBS.glob("*_visa.md"), key=lambda p: p.stat().st_mtime)
    visa_text = visa_file.read_text(encoding="utf-8")
    date = re.search(r"(\d{4}-\d{2}-\d{2})", visa_file.name).group(1)
    src = re.search(r"Source list: (\S+\.md)", visa_text)
    rows = source_rows(JOBS / (src.group(1) if src else visa_file.name.replace("_visa.md", ".md")))
    jd_dir = JOBS / "jd_visa" / date

    jobs = []
    for j in parse_visa_file(visa_file):
        link = re.search(r"\((https?://[^)]+)\)", j.visa)
        jobs.append(dict(
            city=j.city, company=j.company, title=j.title, listing_url=j.url,
            section="linkedin" if "linkedin." in j.url else "company_site",
            visa=dict(verdict="weak" if "⚠️" in j.visa else "yes", detail=re.sub(r"\s+", " ", j.visa),
                      source=link.group(1) if link else None, found_by="visa check"),
            **description(j.city, j.company, j.title, j.url, jd_dir, (rows.get(j.url) or {}).get("jd"))))

    research_file = JOBS / f"visa_research_{date}.json"
    research = json.loads(research_file.read_text(encoding="utf-8")) if research_file.exists() else []
    sponsors = {(r["company"], r["city"]): r for r in research if r["verdict"] in ("yes", "weak")}
    for url, r in rows.items():
        if (hit := sponsors.get((r["company"], r["city"]))):
            jobs.append(dict(
                city=r["city"], company=r["company"], title=r["title"], listing_url=url,
                section="linkedin" if "linkedin." in url else "company_site",
                visa=dict(verdict=hit["verdict"], detail=hit["note"], source=hit["source"] or None,
                          found_by="deeper research (Google question)"),
                **description(r["city"], r["company"], r["title"], url, jd_dir, r["jd"])))

    # Visa unclear (no public info even after deeper research): processed too, flagged in the results.
    unclear_file = JOBS / f"unclear_{date}.md"
    for j in parse_visa_file(unclear_file) if unclear_file.exists() else []:
        jobs.append(dict(
            city=j.city, company=j.company, title=j.title, listing_url=j.url,
            section="linkedin" if "linkedin." in j.url else "company_site",
            visa=dict(verdict="unclear", detail="No public visa info found - confirm with the recruiter",
                      source=None, found_by="visa unclear"),
            **description(j.city, j.company, j.title, j.url, jd_dir, (rows.get(j.url) or {}).get("jd"))))

    scored = [j for j in jobs if j["resume_match"]]
    out = dict(
        date=date, visa_file=visa_file.name, generated=f"{datetime.now():%Y-%m-%d %H:%M}",
        base_resume="Abhinav_kaushik_AI_ML.pdf",
        counts=dict(jobs=len(jobs),
                    from_visa_check=sum(j["visa"]["found_by"] == "visa check" for j in jobs),
                    from_deeper_research=sum(j["visa"]["found_by"].startswith("deeper") for j in jobs),
                    visa_unclear=sum(j["visa"]["verdict"] == "unclear" for j in jobs),
                    visa_weak=sum(j["visa"]["verdict"] == "weak" for j in jobs),
                    with_description=sum(j["description"] is not None for j in jobs),
                    resume_scored=len(scored),
                    shortlisted_60_plus=sum(j["resume_match"]["score"] >= MIN_MATCH for j in scored
                                            if j["visa"]["verdict"] != "unclear"),
                    unclear_60_plus=sum(j["resume_match"]["score"] >= MIN_MATCH for j in scored
                                        if j["visa"]["verdict"] == "unclear")),
        jobs=sorted(jobs, key=lambda j: (j["section"] != "company_site",
                                         -(j["resume_match"]["score"] if j["resume_match"] else -1),
                                         j["city"], j["company"])))
    path = JOBS / f"visa_jobs_{date}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["counts"]), "->", path)


if __name__ == "__main__":
    main()
