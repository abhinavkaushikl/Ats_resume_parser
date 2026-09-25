#!/usr/bin/env python3
"""
job_report.py - the one results file: JOB_RESULTS.md in the project root. Every visa-sponsoring job
(jobs/visa_jobs_<date>.json) with company, link, resume match (matched / missing skills), the unclear-visa
jobs that still match, the visa research, and the numbers for the analysis.

Output
  JOB_RESULTS.md   (rewritten each run; the date is inside)

Usage
  .venv/bin/python job_report.py                                  # newest jobs/visa_jobs_*.json
  .venv/bin/python job_report.py jobs/visa_jobs_2026-09-25.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from jd_extractor import slug
from job_match import MIN_MATCH

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
STOP = set("""a an and or the of in to for with on at by from as is are be experience experienced explicit explicitly
direct demonstrated proven strong solid hands hands-on knowledge understanding familiarity ability skills skill
evidence using use working work years year level e.g etc such similar specific specifically related relevant
background track record""".split())


def cell(s: str) -> str:
    return (s or "").replace("|", "/").replace("\n", " ")


def jd_link(j: dict, date: str) -> str:
    """Links to the saved JD file and, once tailor_all.py has run, the tailored resume + judge score."""
    stem = f"{slug(j['company'])}_{slug(j['title'])}_{j['city']}"
    f = JOBS / "jd_visa" / date / f"{stem}.md"
    jd = f"[JD](jobs/jd_visa/{date}/{stem}.md)" if f.exists() else "–"
    index_file = ROOT / "applications" / date / "index.json"
    t = json.loads(index_file.read_text(encoding="utf-8")).get(stem) if index_file.exists() else None
    if not t:
        return f"{jd} | – | – | –"
    judge = f"{t['hr_score']}/100" if t.get("hr_score") is not None else "–"
    apply = f"[Apply]({t['apply_url']})" if t.get("apply_url") else "–"
    return f"{jd} | [Resume](applications/{date}/{t['resume']}) | {judge} | {apply}"


def row(j: dict, date: str = "") -> str:
    m = j["resume_match"]
    visa = {"yes": "yes", "weak": "⚠️ weak"}.get(j["visa"]["verdict"], "❔ unclear")
    src = f" ([source]({j['visa']['source']}))" if j["visa"].get("source") else ""
    return (f"| {m['score']}% | {cell(j['company'])} | [{cell(j['title'])}]({j['listing_url']}) | {j['city']} | "
            f"{visa}{src} | {cell('; '.join(m['matched'][:4]))} | {cell('; '.join(m['missing'][:4]))} |"
            + (f" {jd_link(j, date)} |" if date else ""))


def gap_terms(jobs: list[dict]) -> list[tuple[str, int]]:
    """Most frequent words in the missing skills of shortlisted-or-close jobs (one count per job)."""
    c = Counter()
    for j in jobs:
        words = set()
        for miss in j["resume_match"]["missing"]:
            words |= {w for w in re.findall(r"[a-z][a-z0-9+#.\-]{2,}", miss.lower()) if w not in STOP}
        c.update(words)
    return c.most_common(12)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_file", nargs="?", type=Path)
    a = ap.parse_args()
    src = a.json_file or max(JOBS.glob("visa_jobs_*.json"), key=lambda p: p.stat().st_mtime)
    d = json.loads(src.read_text(encoding="utf-8"))
    everything = d["jobs"]
    jobs = [j for j in everything if j["visa"]["verdict"] != "unclear"]          # visa yes / weak
    unclear = [j for j in everything if j["visa"]["verdict"] == "unclear"]
    unclear_scored = [j for j in unclear if j["resume_match"]]
    unclear_top = sorted((j for j in unclear_scored if j["resume_match"]["score"] >= MIN_MATCH),
                         key=lambda j: -j["resume_match"]["score"])
    scored = [j for j in jobs if j["resume_match"]]
    top = sorted((j for j in scored if j["resume_match"]["score"] >= MIN_MATCH), key=lambda j: -j["resume_match"]["score"])
    low = sorted((j for j in scored if j["resume_match"]["score"] < MIN_MATCH), key=lambda j: -j["resume_match"]["score"])
    unscored = [j for j in jobs if not j["resume_match"]]
    head = "| Match | Company | Job | City | Visa | Matched | Missing |\n|---|---|---|---|---|---|---|"

    L = [f"# Job results - {d['date']}", "",
         f"Visa-sponsoring AI/ML jobs matched against {d['base_resume']}. Generated {d['generated']}.", "",
         "## Summary", "",
         f"- Visa-sponsoring jobs: **{len(jobs)}** ({d['counts']['from_visa_check']} from the visa check, "
         f"{d['counts']['from_deeper_research']} added by deeper research; "
         f"{d['counts']['visa_weak']} rest on weak visa evidence)",
         f"- Scored against the resume: **{len(scored)}** · **{len(top)} match {MIN_MATCH}%+** · "
         f"{len(low)} below {MIN_MATCH}% · {len(unscored)} not scored (no description found)",
         f"- Visa unclear (no public info): **{len(unclear)}** jobs · {len(unclear_scored)} scored · "
         f"**{len(unclear_top)} match {MIN_MATCH}%+** - listed separately, confirm visa with the recruiter",
         f"- **To apply: {len(top) + len(unclear_top)}** ({len(top)} visa yes/weak + {len(unclear_top)} visa unclear)",
         ""]
    for title, part in (("Company career sites", "company_site"), ("LinkedIn", "linkedin")):
        rows = [row(j, d["date"]) for j in top if j["section"] == part]
        L += [f"## Shortlist {MIN_MATCH}%+ - {title} ({len(rows)})", ""]
        L += [head.replace(" |\n|", " | JD | Resume | Judge | Apply |\n|", 1) + "---|---|---|---|", *rows, ""] if rows else ["_None._", ""]

    L += [f"## Visa unclear - match {MIN_MATCH}%+ ({len(unclear_top)} of {len(unclear_scored)} scored)", "",
          "No public visa info found for these companies, but the resume matches. Apply, and ask the "
          "recruiter early: \"Do you sponsor a work permit / Blue Card for non-EU hires for this role?\"", ""]
    L += [head.replace(" |\n|", " | JD | Resume | Judge | Apply |\n|", 1) + "---|---|---|---|", *[row(j, d["date"]) for j in unclear_top], ""] \
        if unclear_top else ["_None._", ""]

    L += [f"## Below {MIN_MATCH}% ({len(low)})", ""]
    L += [head, *[row(j) for j in low], ""] if low else ["_None._", ""]

    L += [f"## Not scored - no job description found ({len(unscored)})", "",
          "Open the posting to read the description yourself.", "",
          "| Company | Job | City | Visa | Posting |", "|---|---|---|---|---|"]
    L += [f"| {cell(j['company'])} | {cell(j['title'])} | {j['city']} | "
          f"{'yes' if j['visa']['verdict'] == 'yes' else '⚠️ weak'} | "
          f"[{'LinkedIn' if 'linkedin.' in j['listing_url'] else 'Company site'}]({j['listing_url']}) |"
          for j in sorted(unscored, key=lambda j: (j["city"], j["company"]))]

    research_file = JOBS / f"visa_research_{d['date']}.json"
    if research_file.exists():
        r = json.loads(research_file.read_text(encoding="utf-8"))
        n = Counter(x["verdict"] for x in r)
        found = sorted({f"{x['company']} ({x['city']})" for x in r if x["verdict"] in ("yes", "weak")})
        L += ["", "## Visa research on removed companies", "",
              f"{len(r)} companies checked again: {n.get('yes', 0)} sponsor, {n.get('weak', 0)} weak yes, "
              f"{n.get('no', 0)} no, {n.get('agency', 0)} recruitment agencies, {n.get('unclear', 0)} still unclear.",
              "", "Added back: " + (", ".join(found) or "none")]

    # Numbers for the analysis
    by_city = Counter(j["city"] for j in top)
    bands = Counter(("85-100" if s >= 85 else "70-84" if s >= 70 else "60-69" if s >= 60 else "40-59" if s >= 40
                     else "0-39") for s in (j["resume_match"]["score"] for j in scored))
    L += ["", "## Analysis data", "",
          "**Score bands:** " + " · ".join(f"{b}: {bands.get(b, 0)}" for b in ("85-100", "70-84", "60-69", "40-59", "0-39")),
          "",
          "**Shortlist by city:** " + (" · ".join(f"{c} {n}" for c, n in by_city.most_common()) or "none"), "",
          "**Shortlisted jobs with weak visa evidence:** "
          + (", ".join(f"{j['company']} ({j['city']})" for j in top if j["visa"]["verdict"] != "yes") or "none"), "",
          "**Most common gaps (words in 'missing', jobs scoring 50%+):** "
          + ", ".join(f"{w} ({n})" for w, n in gap_terms([j for j in scored if j["resume_match"]["score"] >= 50])),
          "", "**Blockers seen:** "
          + (", ".join(sorted({b for j in scored for b in j["resume_match"].get("blockers", [])})) or "none"), ""]
    out = ROOT / "JOB_RESULTS.md"
    text = "\n".join(L) + "\n"
    # Keep the same day's written "## Analysis" (added by Claude after the first build) when rebuilding.
    old = out.read_text(encoding="utf-8") if out.exists() else ""
    if old.startswith(f"# Job results - {d['date']}") and "\n## Analysis\n" in old:
        analysis = old.split("\n## Analysis\n", 1)[1].split("\n## ", 1)[0].strip()
        i = text.index("\n## Shortlist")
        text = f"{text[:i]}\n## Analysis\n\n{analysis}\n{text[i:]}"
    out.write_text(text, encoding="utf-8")
    print(f"{len(top)} shortlisted of {len(scored)} scored ({len(jobs)} visa jobs) -> {out}")


if __name__ == "__main__":
    main()
