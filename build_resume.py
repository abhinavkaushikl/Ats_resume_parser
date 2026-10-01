#!/usr/bin/env python3
"""
build_resume.py - builds the tailored resume + cover letter from a tailoring.json written by Claude
(the /tailor-resumes skill). No LLM calls here: the base resume is parsed, only the parts in
tailoring.json change, and the LaTeX template renders it (PDF when a LaTeX engine is installed).

What changes (subtle tailoring):
  title    -> the JD's job title (kept only if it fits the resume's seniority), in the resume and cover letter
  role     -> "current_role_title": the current (United Health Group) role's title, from ROLE_TITLES only
              (Data Scientist JD -> Senior Data Scientist, AI Engineer JD -> Senior AI Engineer, ...)
  summary  -> the tweaked summary
  language -> "German: A1" is listed only for a job in Germany / Austria / Switzerland or a JD that asks for
              German; otherwise the Languages section shows English only
  bullets  -> "experience_edits": existing experience bullets reworded so the JD's words blend in; same facts,
              exactly the same numbers, max 2 lines; a bad edit is skipped (warning) and the base bullet kept
  project  -> ONE new project, inserted right after the first project (Think Tree), company name removed
  variant  -> for a JD heavy on time series / forecasting, the fixed time-series experience bullets from
              resume_variants.json (written by Abhinav, not an LLM); "experience_variant" in
              tailoring.json overrides the automatic pick ("timeseries" or "base")
Everything else - skills, education, the other projects, Think Tree, the variant bullets - is the base resume.

Folder per job: applications/<date>/<jd-file-stem>/
  in:  tailoring.json (Claude), judge.json (Claude judge, optional)
  out: <Name>_Resume.tex/.pdf, <Name>_Cover_Letter.tex/.pdf, resume.txt (for the judge), project_brief.md
Index: applications/<date>/index.json (read by job_report.py)

tailoring.json
  {"company": "", "role": "", "city": "", "company_profile": "",
   "title": "", "current_role_title": "Senior AI Engineer", "summary": "",
   "experience_edits": [{"original": "<first words of a base bullet>", "new": "<reworded bullet>"}],
   "project": {"name": "", "bullets": ["", ""], "technologies": [""]},
   "cover_letter": {"greeting": "Dear Hiring Team,", "paragraphs": ["", "", ""], "closing": "Sincerely,"},
   "jd_keywords": [""], "experience_variant": "timeseries | base (optional)"}
judge.json
  {"score": 0, "decision": "", "strengths": [""], "gaps": [""]}

Usage
  .venv/bin/python build_resume.py --date 2026-09-25            # build every job not built yet + index
  .venv/bin/python build_resume.py --date 2026-09-25 --rebuild  # rebuild all
  .venv/bin/python build_resume.py --date 2026-09-25 --index    # only refresh index.json (after judging)
  .venv/bin/python build_resume.py --dir gpt_automation/tailored_applications_2026-09-26   # any folder of
      job folders (e.g. GPT's tailoring.json files); each job's JD is <job>/job_description.md
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
from ats_tailor.variants import apply_variant, pick_variant

ROOT = Path(__file__).resolve().parent
APPS = ROOT / "applications"
log = logging.getLogger("build_resume")

# Titles the current role may take (it is held at a data science / ML / AI level, so each is true).
CURRENT_ROLE_COMPANY = "United Health Group"
ROLE_TITLES = ("Senior AI Engineer", "Senior Data Scientist", "Senior Machine Learning Engineer",
               "Senior GenAI Engineer", "Senior Applied Scientist")
MAX_BULLET_CHARS = 225  # about 2 lines on the page
_NUM = re.compile(r"\d[\d,.]*\d%?|\d%?")


_GERMAN_PLACES = re.compile(
    r"\b(?:german|deutsch|austria|österreich|osterreich|switzerland|schweiz|berlin|munich|münchen|munchen|hamburg|"
    r"frankfurt|cologne|köln|koln|stuttgart|düsseldorf|dusseldorf|leipzig|dresden|hanover|hannover|nuremberg|"
    r"nürnberg|nurnberg|karlsruhe|bonn|heidelberg|mannheim|essen|dortmund|bremen|potsdam|vienna|wien|zurich|"
    r"zürich|basel|bern|geneva|lausanne|zug|graz|linz|salzburg|innsbruck)\b", re.I)


def _german_job(city: str, jd_text: str) -> bool:
    """A job in a German-speaking country, or a JD that mentions German / Deutsch."""
    location = next((l for l in jd_text[:3000].splitlines() if l.startswith("- **Location:**")), "")
    return bool(_GERMAN_PLACES.search(f"{city} {location}") or re.search(r"\bgerman\b|deutsch", jd_text, re.I))


def _numbers(text: str) -> list[str]:
    return sorted(_NUM.findall(text))


def _set_role_title(resume, title: str, warnings: list) -> None:
    role = next((e for e in resume.experience if CURRENT_ROLE_COMPANY.lower() in e.company.lower()), None)
    if not title or role is None or title == role.title:
        return
    if title not in ROLE_TITLES:
        warnings.append(f"Role title '{title}' not allowed (use one of {', '.join(ROLE_TITLES)}); kept '{role.title}'.")
        return
    role.title = title


def _apply_edits(resume, locked: set[str], edits: list, company: str, warnings: list) -> list[dict]:
    """Reword existing experience bullets. Each edit must match one bullet by its start, keep exactly the
    same numbers, stay within 2 lines and not name the company; otherwise it is skipped."""
    done = []
    for ed in edits or []:
        old, new = plain_text(ed.get("original", "")).strip(), _no_company(plain_text(ed.get("new", "")).strip(), company)
        hits = [(e, i) for e in resume.experience for i, b in enumerate(e.bullets) if old and b.startswith(old)]
        why = ("no bullet starts with it" if not hits else "matches several bullets" if len(hits) > 1
               else "variant bullet (never edited)" if hits[0][0].bullets[hits[0][1]] in locked
               else "numbers changed" if _numbers(new) != _numbers(hits[0][0].bullets[hits[0][1]])
               else f"longer than {MAX_BULLET_CHARS} characters" if len(new) > MAX_BULLET_CHARS
               else "company name" if len(company) > 2 and company.lower() in new.lower()
               else "empty" if not new else "")
        if why:
            warnings.append(f"Edit skipped ({why}): '{old[:60]}'")
            continue
        role, i = hits[0]
        done.append({"role": role.title, "before": role.bullets[i], "after": new})
        role.bullets[i] = new
    if done:
        warnings.append(f"Experience bullets reworded: {len(done)}")
    return done


def _no_company(text: str, company: str) -> str:
    return _scrub_company(SimpleNamespace(name=text, bullets=[], technologies=[]), company).name


def _jd_path(folder: Path) -> Path:
    """The job's JD file: jobs/jd_visa/<date>/<job>.md, skipped/ for 50-59% jobs, or job_description.md in
    the application folder (where cleanup.py moves it)."""
    day = ROOT / "jobs" / "jd_visa" / folder.parent.name
    candidates = (day / f"{folder.name}.md", day / "skipped" / f"{folder.name}.md", folder / "job_description.md")
    return next((p for p in candidates if p.exists()), candidates[0])


def build(folder: Path, settings) -> dict:
    t = json.loads((folder / "tailoring.json").read_text(encoding="utf-8"))
    company, city = t.get("company", ""), t.get("city", "")
    jd_file = _jd_path(folder)
    jd_text = jd_file.read_text(encoding="utf-8") if jd_file.exists() else ""
    # Experience variant (resume_variants.json): tailoring.json's "experience_variant" ("base" = none),
    # else picked from the JD, the same way job_match.py picks it for scoring.
    variant = t.get("experience_variant") or pick_variant(jd_text)
    variant = None if variant == "base" else variant
    base = apply_variant(load_base(settings.base_resume_path, settings.base_resume_fixes), variant)
    resume = base.model_copy(deep=True)
    warnings = [f"Experience variant: {variant}"] if variant else []
    plain = load_base(settings.base_resume_path, settings.base_resume_fixes)
    locked = {b for e in base.experience for b in e.bullets} - {b for e in plain.experience for b in e.bullets}
    _set_role_title(resume, t.get("current_role_title", ""), warnings)
    edits = _apply_edits(resume, locked, t.get("experience_edits"), company, warnings)
    if not _german_job(city, jd_text):
        resume.languages = [l for l in resume.languages if not l.lower().startswith("german")]

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
        jd = jd_text
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

    jd_head = jd_text[:3000]
    link = lambda k: (m.group(1).strip() if (m := re.search(rf"^- \*\*{re.escape(k)}:\*\* (\S+)", jd_head, re.M)) else None)
    listing_url, apply_url = link("Original listing"), link("JD source (Playwright)")
    # Also parse the "**Application:** [text](url)" format used by skill-provided JD summaries.
    if not listing_url:
        if m := re.search(r"^\*\*Application:\*\*\s+\[.*?\]\((\S+?)\)", jd_head, re.M):
            listing_url = m.group(1).rstrip(")")
    plan = SimpleNamespace(analysis=SimpleNamespace(role=t.get("role", ""), company=company, location=city,
                                                    company_profile=t.get("company_profile", ""),
                                                    apply_url=apply_url or listing_url))
    if brief := _project_brief(resume, SimpleNamespace(jd_keywords=t.get("jd_keywords", [])), plan):
        (folder / "project_brief.md").write_text(brief, encoding="utf-8")
    report = dict(company=company, city=city, role=t.get("role", ""), pages=pages, warnings=warnings,
                  headline=resume.headline, current_role_title=resume.experience[0].title, experience_edits=edits,
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
    ap.add_argument("--date")
    ap.add_argument("--dir", type=Path, help="folder of job folders to build instead of applications/<date>/")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--index", action="store_true", help="only refresh index.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if not (a.date or a.dir):
        ap.error("give --date or --dir")
    day = a.dir.resolve() if a.dir else APPS / a.date
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
