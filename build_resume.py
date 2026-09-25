#!/usr/bin/env python3
"""
build_resume.py - builds the tailored resume + cover letter from a tailoring.json written by Claude
(the /tailor-resumes skill). No LLM calls here: the base resume is parsed, only the parts in
tailoring.json change, and the LaTeX template renders it (PDF when a LaTeX engine is installed).

What changes (subtle tailoring):
  title    -> the JD's job title (kept only if it fits the resume's seniority)
  summary  -> the tweaked summary
  project  -> ONE new project, inserted right after the first project (Think Tree), company name removed
Everything else - experience, skills, education, the other projects, Think Tree - is the base resume.

Folder per job: applications/<date>/<jd-file-stem>/
  in:  tailoring.json (Claude), judge.json (Claude judge, optional)
  out: <Name>_Resume.tex/.pdf, <Name>_Cover_Letter.tex/.pdf, resume.txt (for the judge), project_brief.md
Index: applications/<date>/index.json (read by job_report.py)

tailoring.json
  {"company": "", "role": "", "city": "", "company_profile": "",
   "title": "", "summary": "",
   "project": {"name": "", "bullets": ["", ""], "technologies": [""]},
   "cover_letter": {"greeting": "Dear Hiring Team,", "paragraphs": ["", "", ""], "closing": "Sincerely,"},
   "jd_keywords": [""]}
judge.json
  {"score": 0, "decision": "", "strengths": [""], "gaps": [""]}

Usage
  .venv/bin/python build_resume.py --date 2026-09-25            # build every job not built yet + index
  .venv/bin/python build_resume.py --date 2026-09-25 --rebuild  # rebuild all
  .venv/bin/python build_resume.py --date 2026-09-25 --index    # only refresh index.json (after judging)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from types import SimpleNamespace

from ats_tailor.base_resume import load_base
from ats_tailor.config import get_settings
from ats_tailor.latex import LatexError, compile_pdf, pdf_page_count, render_cover_letter, render_resume
from ats_tailor.pipeline import TailoringPipeline, _project_brief, _scrub_company, _slug, _trim_once
from ats_tailor.reflection import _aligned_headline
from ats_tailor.schemas import CoverLetter, Project
from ats_tailor.text import plain_text

ROOT = Path(__file__).resolve().parent
APPS = ROOT / "applications"
log = logging.getLogger("build_resume")


def _no_company(text: str, company: str) -> str:
    return _scrub_company(SimpleNamespace(name=text, bullets=[], technologies=[]), company).name


def build(folder: Path, settings) -> dict:
    t = json.loads((folder / "tailoring.json").read_text(encoding="utf-8"))
    company, city = t.get("company", ""), t.get("city", "")
    base = load_base(settings.base_resume_path, settings.base_resume_fixes)
    resume = base.model_copy(deep=True)
    warnings = []

    if t.get("title") and (headline := _aligned_headline(base, _no_company(t["title"], company))):
        resume.headline = headline
    elif t.get("title"):
        warnings.append(f"Title '{t['title']}' not used (seniority/fit check); kept '{base.headline}'.")
    if summary := _no_company(plain_text(t.get("summary", "")), company):
        resume.summary = summary

    p = t.get("project") or {}
    if p.get("bullets"):
        np = _scrub_company(SimpleNamespace(name=plain_text(p.get("name", "")),
                                            bullets=[plain_text(b) for b in p["bullets"]],
                                            technologies=[plain_text(x) for x in p.get("technologies", [])]), company)
        resume.projects.insert(1, Project(name=np.name, bullets=np.bullets, technologies=np.technologies,
                                          added=len(np.bullets), is_new=True))
    else:
        warnings.append("No new project in tailoring.json.")
    if len(company) > 2 and company.lower() in resume.as_text().lower():
        warnings.append(f"The company name '{company}' still appears in the resume - check it.")

    stem = _slug(settings.candidate_name)  # no company in file names: recruiters see them
    resume_tex = folder / f"{stem}_Resume.tex"
    pages, pdf_ok = None, True
    try:  # fit to the page limit by trimming only ADDED bullets (never base content)
        while True:
            resume_tex.write_text(render_resume(resume, settings), encoding="utf-8")
            pages = pdf_page_count(compile_pdf(resume_tex, settings))
            if pages <= settings.max_resume_pages:
                break
            removed = _trim_once(resume, base, t.get("jd_keywords", []), set())
            if not removed:
                warnings.append(f"Resume is {pages} pages (target {settings.max_resume_pages}).")
                break
            warnings.append(f"Trimmed to fit: {removed}")
    except LatexError as exc:
        pdf_ok = False
        warnings.append(f"No PDF ({exc}). Install a LaTeX engine: brew install tectonic")
    (folder / "resume.txt").write_text(resume.as_text(), encoding="utf-8")

    cl = t.get("cover_letter") or {}
    letter_file = None
    if cl.get("paragraphs"):
        letter = CoverLetter(company=company, role=t.get("role", ""), greeting=cl.get("greeting") or "Dear Hiring Team,",
                             paragraphs=[plain_text(x) for x in cl["paragraphs"]], closing=cl.get("closing") or "Sincerely,")
        helper = SimpleNamespace(settings=settings)
        helper._motivation = lambda loc: TailoringPipeline._motivation(helper, loc)
        letter = TailoringPipeline._ensure_motivation(helper, letter, city)
        jd_file = ROOT / "jobs" / "jd_visa" / folder.parent.name / f"{folder.name}.md"
        jd = jd_file.read_text(encoding="utf-8") if jd_file.exists() else ""
        letter, notes = TailoringPipeline._drop_unsupported_numbers(helper, letter, f"{resume.as_text()}\n{jd}")
        warnings += notes
        letter_tex = folder / f"{stem}_Cover_Letter.tex"
        letter_tex.write_text(render_cover_letter(letter, resume.headline, settings), encoding="utf-8")
        letter_file = letter_tex.name
        if pdf_ok:
            try:
                compile_pdf(letter_tex, settings)
                letter_file = letter_tex.with_suffix(".pdf").name
            except LatexError as exc:
                warnings.append(f"Cover letter PDF failed: {exc}")

    jd_head = (ROOT / "jobs" / "jd_visa" / folder.parent.name / f"{folder.name}.md")
    jd_head = jd_head.read_text(encoding="utf-8")[:3000] if jd_head.exists() else ""
    link = lambda k: (m.group(1).strip() if (m := re.search(rf"^- \*\*{re.escape(k)}:\*\* (\S+)", jd_head, re.M)) else None)
    listing_url, apply_url = link("Original listing"), link("JD source (Playwright)")
    plan = SimpleNamespace(analysis=SimpleNamespace(role=t.get("role", ""), company=company, location=city,
                                                    company_profile=t.get("company_profile", ""),
                                                    apply_url=apply_url or listing_url))
    if brief := _project_brief(resume, SimpleNamespace(jd_keywords=t.get("jd_keywords", [])), plan):
        (folder / "project_brief.md").write_text(brief, encoding="utf-8")
    report = dict(company=company, city=city, role=t.get("role", ""), pages=pages, warnings=warnings,
                  apply_url=apply_url or listing_url, listing_url=listing_url,
                  resume=f"{folder.name}/{resume_tex.with_suffix('.pdf').name if pdf_ok else resume_tex.name}",
                  cover_letter=f"{folder.name}/{letter_file}" if letter_file else None,
                  project_brief=f"{folder.name}/project_brief.md" if brief else None)
    (folder / "build.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


RUBRIC_MAX = {"tech_stack": 30, "experience": 25, "company_project": 20, "ats_keywords": 15, "credibility": 10}


def judge_score(j: dict) -> int | None:
    """The score is the sum of the criteria, each capped at its maximum (not the judge's own arithmetic)."""
    c = j.get("criteria") or {}
    if all(k in c for k in RUBRIC_MAX):
        return sum(min(int(c[k]), m) for k, m in RUBRIC_MAX.items())
    return j.get("score")


def refresh_index(day: Path) -> dict:
    index = {}
    for folder in sorted(p for p in day.iterdir() if (p / "build.json").exists()):
        entry = json.loads((folder / "build.json").read_text(encoding="utf-8"))
        judge = folder / "judge.json"
        entry["hr_score"] = judge_score(json.loads(judge.read_text(encoding="utf-8"))) if judge.exists() else None
        index[folder.name] = entry
    (day / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--index", action="store_true", help="only refresh index.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    day = APPS / a.date
    if not a.index:
        settings = get_settings()
        todo = [p for p in sorted(day.iterdir()) if (p / "tailoring.json").exists()
                and (a.rebuild or not (p / "build.json").exists())]
        for i, folder in enumerate(todo, 1):
            try:
                r = build(folder, settings)
                print(f"[{i}/{len(todo)}] built {folder.name} ({r['pages'] or '?'} pages, "
                      f"{len(r['warnings'])} warnings)", flush=True)
                for w in r["warnings"]:
                    print(f"    - {w}", flush=True)
            except Exception as exc:
                print(f"[{i}/{len(todo)}] FAILED {folder.name}: {exc}", flush=True)
    index = refresh_index(day)
    judged = [e["hr_score"] for e in index.values() if e["hr_score"] is not None]
    print(f"{len(index)} built, {len(judged)} judged -> {day / 'index.json'}")


if __name__ == "__main__":
    main()
