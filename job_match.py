#!/usr/bin/env python3
"""
job_match.py - how well a job description fits the base resume, 0-100 (an honest fit, not an ATS trick).

Jobs scoring MIN_MATCH (60) or more are shortlisted; the rest are skipped. Used by jd_extractor.py and
daily_jobs.py, and on its own for JD files that were already saved.

Usage
  .venv/bin/python job_match.py jobs/jd_visa/2026-09-25            # score every JD file in the folder,
                                                                   # move < 60 into skipped/, write SHORTLIST.md
  .venv/bin/python job_match.py jobs/jd_visa/2026-09-25 --min 70
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from ats_tailor.base_resume import load_base
from ats_tailor.config import get_settings
from ats_tailor.llm import LLMClient
from ats_tailor.variants import apply_variant, pick_variant

MIN_MATCH = 60
MAX_JD_CHARS = 9000
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "outputs" / ".cache"

SYSTEM = """You are an experienced technical recruiter. Judge how well the candidate's CURRENT resume fits the
job description, as an honest 0-100 match. Judge only real evidence in the resume; do not assume skills it
does not show, and do not give credit for something the candidate could learn.

Weigh, in this order:
1. Must-have requirements (core skills, tools, domain, years and level of experience) - most of the score.
2. The kind of work: does the candidate's actual experience look like this job's day-to-day work?
3. Nice-to-have requirements - a little.
Hard blockers (a required language the resume does not show, a required degree or clearance it lacks, a
completely different field) keep the score low whatever else matches.

Scale: 85-100 strong fit, most must-haves clearly shown · 70-84 good fit, a few gaps · 60-69 reasonable
fit, worth applying · 40-59 partial fit, important gaps · 0-39 poor fit or different role.

Return JSON: {"score": int, "matched": [must-haves the resume shows], "missing": [must-haves it lacks],
"blockers": [hard blockers, if any], "reason": "one sentence"}"""


class Match(BaseModel):
    score: int = Field(ge=0, le=100)
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    reason: str = ""


@lru_cache
def _ctx(variant: str | None = None) -> tuple[LLMClient, str]:
    """The LLM client and the resume text - with the experience variant for this kind of JD, e.g. the
    time-series bullets for a forecasting-heavy JD (resume_variants.json), so the job is scored against
    the same resume that would be sent."""
    s = get_settings()
    resume = apply_variant(load_base(s.base_resume_path, s.base_resume_fixes), variant).as_text()
    if s.extra_skills:
        resume += f"\n\nOther skills the candidate has: {s.extra_skills}"
    return LLMClient(s), resume


def _cache_file(jd: str) -> Path:
    _, resume = _ctx(pick_variant(jd))
    key = hashlib.sha256(f"{SYSTEM}\n{resume}\n{jd.strip()[:MAX_JD_CHARS]}".encode()).hexdigest()[:16]
    return CACHE / f"match_{key}.json"


def cached(jd: str) -> Match | None:
    """The saved score for this JD, without calling the LLM (None if it was never scored)."""
    f = _cache_file(jd)
    return Match.model_validate_json(f.read_text(encoding="utf-8")) if f.exists() else None


def score(jd: str) -> Match:
    """Fit of this JD to the base resume. Cached per (resume, JD) so re-runs give the same answer."""
    if (m := cached(jd)) is not None:
        return m
    llm, resume = _ctx(pick_variant(jd))
    jd = jd.strip()[:MAX_JD_CHARS]
    f = _cache_file(jd)
    m = llm.structured(SYSTEM, f"JOB DESCRIPTION:\n{jd}", Match, prefix=f"CANDIDATE RESUME:\n{resume}",
                       temperature=0.0, reasoning_effort="medium")
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(m.model_dump_json(indent=1), encoding="utf-8")
    return m


def verdict(m: Match | None, min_match: int = MIN_MATCH) -> str:
    if m is None:
        return "not scored"
    return f"{m.score}% - {'shortlisted' if m.score >= min_match else 'skipped'}: {m.reason}"


def match_lines(m: Match, min_match: int = MIN_MATCH) -> list[str]:
    """Markdown bullet lines for a JD file header."""
    L = [f"- **Resume match:** {verdict(m, min_match)}"]
    if m.matched:
        L.append(f"- **Matched:** {'; '.join(m.matched)}")
    if m.missing:
        L.append(f"- **Missing:** {'; '.join(m.missing)}")
    if m.blockers:
        L.append(f"- **Blockers:** {'; '.join(m.blockers)}")
    return L


def _jd_body(text: str) -> str:
    return text.split("## Job description", 1)[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--min", type=int, default=MIN_MATCH)
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)
    skipped = a.folder / "skipped"
    files = sorted(p for p in a.folder.glob("*.md") if p.name not in ("README.md", "SHORTLIST.md"))
    files += sorted(skipped.glob("*.md")) if skipped.exists() else []
    rows = []
    for i, f in enumerate(files, 1):
        text = f.read_text(encoding="utf-8")
        m = score(_jd_body(text))
        # Refresh the match lines in the file header, then keep it in the folder or move it to skipped/.
        text = re.sub(r"^- \*\*(Resume match|Matched|Missing|Blockers):\*\*.*\n", "", text, flags=re.M)
        text = text.replace("\n## Job description", "\n".join([""] + match_lines(m, a.min)) + "\n\n## Job description", 1)
        dest = (a.folder if m.score >= a.min else skipped) / f.name
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        if dest != f:
            f.unlink()
        title = text.splitlines()[0].lstrip("# ")
        rows.append((m.score, title, dest.relative_to(a.folder), m))
        print(f"[{i}/{len(files)}] {m.score:3d}% {'✅' if m.score >= a.min else '⏭ '} {f.stem}", flush=True)

    rows.sort(key=lambda r: -r[0])
    keep = [r for r in rows if r[0] >= a.min]
    L = [f"# Shortlist - resume match {a.min}%+", "",
         f"{len(keep)} of {len(rows)} jobs match the base resume by {a.min}% or more. "
         f"The other {len(rows) - len(keep)} are in skipped/.", "",
         "| Match | Job | File | Missing |", "|---|---|---|---|"]
    for s, title, path, m in rows:
        L.append(f"| {s}% {'✅' if s >= a.min else '⏭'} | {title} | [{path}]({path}) | {', '.join(m.missing[:4])} |")
    (a.folder / "SHORTLIST.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(keep)}/{len(rows)} shortlisted. {a.folder / 'SHORTLIST.md'}")


if __name__ == "__main__":
    main()
