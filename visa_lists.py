#!/usr/bin/env python3
"""
visa_lists.py - split a job list into the two files I use (no job descriptions, no scoring):

  job_lists/<date>/sponsor_jobs.md     visa yes / weak (⚠️) / Gulf-Asia country rule (🌍) - for Claude
  gpt_automation/company_list.md       visa unclear (no evidence yet) - for GPT
                                       (+ gpt_automation/archive/company_list_<date>.md)

Evidence, strongest first: the Claude research file (jobs/visa_research_<date>.json, written in step 2),
the sponsor registers (jobs/register_hits_<date>.json from sponsor_registers.py), the visa answer cache
(jobs/visa_companies.json), the visa hints the job search found. Dropped - listed at the bottom only:
the company says no / needs existing work rights, or a recruitment agency hides the employer.

sponsor_jobs.md uses the visa-file format, so a job I pick can get its JD later with
  .venv/bin/python jd_extractor.py job_lists/<date>/sponsor_jobs.md --only "<company>"

Usage
  .venv/bin/python visa_lists.py jobs/jobs_2026-09-29_1950.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
GPT = ROOT / "gpt_automation"

COUNTRY = {
    "Berlin": "Germany", "Munich": "Germany", "Germany": "Germany", "Amsterdam": "Netherlands",
    "Netherlands": "Netherlands", "Brussels": "Belgium", "Paris": "France", "Copenhagen": "Denmark",
    "Warsaw": "Poland", "Austria": "Austria", "London": "UK", "Romania": "Romania", "Norway": "Norway",
    "Barcelona": "Spain", "Switzerland": "Switzerland", "Sweden": "Sweden", "Italy": "Italy",
    "Luxembourg": "Luxembourg", "Estonia": "Estonia", "Ireland": "Ireland", "Portugal": "Portugal",
    "Dubai": "UAE", "Abu Dhabi": "UAE", "Qatar": "Qatar", "Kuwait": "Kuwait", "Singapore": "Singapore",
    "Japan": "Japan",
}
# No sponsor register exists here, and every foreign hire needs an employer-sponsored work visa
# (UAE / Qatar / Kuwait employment visa, Singapore Employment Pass, Japan work visa).
COUNTRY_RULE = {"Dubai", "Abu Dhabi", "Qatar", "Kuwait", "Singapore", "Japan"}
AGENCY = re.compile(r"\b(recruit\w*|staffing|headhunt\w*|executive search|search (and|&) selection|"
                    r"talent (acquisition|solutions|partners)|personalvermittlung)\b|"
                    r"^(harnham|hays|randstad|adecco|michael page|robert half|james adams|morson|haystack|"
                    r"hunter bond|jobcloud|halian)\b", re.I)
H = ("| | Title | Company | Level | Location | Opened | Visa / Relocation | JD | Source |\n"
     "|---|---|---|---|---|---|---|---|---|")


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def parse_jobs(path: Path):
    """Rows of a daily_jobs.py list: (city, cells) - cells = new, title link, company, level, location,
    opened, visa hint, JD, source."""
    city, out = None, []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## (.+?) \(\d+\)", ln):
            city = m.group(1)
        elif city and ln.startswith("|") and "](" in ln and not ln.startswith("|---"):
            c = [x.strip() for x in ln.strip().strip("|").split("|")]
            if len(c) >= 9 and re.match(r"\[.+\]\(http", c[1]):
                out.append((city, c[:9]))
    return out


def verdict(company, city, hint, research, hits, cache):
    """-> (kind, visa cell / reason). kind: yes | weak | no | agency | unclear."""
    country = COUNTRY.get(city, city)
    r = research.get((company, city))
    if r:
        v, note, src = r["verdict"], r.get("note", ""), r.get("source", "")
        link = f"[source]({src})" if src else "Claude research"
        if v == "yes":
            return "yes", f"Visa: yes · Relocation: not stated · Source: {link}"
        if v == "weak":
            return "weak", f"Visa: yes · Relocation: not stated · Source: {link} ⚠️ weak source, confirm with recruiter"
        if v in ("no", "agency"):
            return v, note or v
        return "unclear", note or "Claude research found nothing"
    if AGENCY.search(company):
        return "agency", "recruitment agency - the real employer isn't named"
    ce = cache.get(f"{company}|{country}", {})
    if ce.get("visa") == "no" or "unlikely" in hint.lower():
        return "no", "says no sponsorship / residents only"
    h = hits.get((company, city))
    if h and h["match"] in ("exact", "candidate"):
        weak = not h["official"] or h["match"] == "candidate"
        cell = f"Visa: yes · Relocation: not stated · Source: [{h['label']}]({h['source']})"
        if h["match"] == "candidate":
            cell += f" (similar name: {h['names'][0]})" if h.get("names") else ""
        return ("weak" if weak else "yes"), cell + (" ⚠️ weak source, confirm with recruiter" if weak else "")
    if ce.get("visa") in ("yes", "weak") and ce.get("src"):
        strong = ce["visa"] == "yes" and ce.get("official")
        reloc = "yes" if ce.get("relocation") == "yes" else "not stated"
        cell = f"Visa: yes · Relocation: {reloc} · Source: [source]({ce['src']})"
        return ("yes" if strong else "weak"), cell + ("" if strong else " ⚠️ weak source, confirm with recruiter")
    if re.search(r"Visa (✅|likely)|Reloc (✅|likely)", hint):
        return "weak", f"Visa: yes · Relocation: see hint · Source: job search hint ({hint}) ⚠️ weak source, confirm with recruiter"
    if city in COUNTRY_RULE:
        return "weak", (f"Visa: yes (employer-sponsored work visa is standard for foreign hires in {country}) · "
                        "Relocation: not stated · Source: country rule 🌍 ⚠️ weak source, confirm with recruiter")
    return "unclear", ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs_file", help="jobs/jobs_<date>_<HHMM>.md from daily_jobs.py")
    ap.add_argument("--window", default="last 24h", help="shown in the headers, e.g. 'last 14 days'")
    a = ap.parse_args()
    src = Path(a.jobs_file)
    day = re.search(r"\d{4}-\d{2}-\d{2}", src.name).group(0) if re.search(r"\d{4}-\d{2}-\d{2}", src.name) \
        else datetime.now().strftime("%Y-%m-%d")
    hits = {(h["company"], h["city"]): h for h in load(JOBS / f"register_hits_{day}.json", [])}
    research = {(r["company"], r["city"]): r for r in load(JOBS / f"visa_research_{day}.json", [])}
    cache = load(JOBS / "visa_companies.json", {})

    sponsor = defaultdict(lambda: {"site": [], "li": []})
    gpt, dropped, cities = [], defaultdict(set), []
    counts = defaultdict(int)
    for city, (new, title, comp, lvl, loc, opened, hint, jd, source) in parse_jobs(src):
        cities.append(city) if city not in cities else None
        kind, cell = verdict(comp, city, hint, research, hits, cache)
        counts[kind] += 1
        if kind in ("yes", "weak"):
            row = f"| {new} | {title} | {comp} | {lvl} | {loc} | {opened.split(' (')[0]} | {cell} | - | {source} |"
            sponsor[city]["li" if source == "LinkedIn" else "site"].append(row)
        elif kind == "unclear":
            name, url = re.match(r"\[(.*)\]\((.*)\)", title).groups()
            checked = "sponsor registers, visa cache, job-ad hints" + ("; Claude research" if research else "")
            gpt.append((comp, name.replace("|", "/"), city, source, checked, url))
        else:
            dropped[kind].add(f"{comp} ({city})")

    n_country = sum("country rule" in r for c in sponsor.values() for r in c["site"] + c["li"])
    n_weak = sum("⚠️" in r for c in sponsor.values() for r in c["site"] + c["li"]) - n_country
    n_sp = counts["yes"] + counts["weak"]

    # 1. sponsor list (visa-file format)
    L = [f"# AI / ML / Data Science jobs - {a.window} - visa sponsorship checked", "",
         f"Source list: {src.name} ({sum(counts.values())} jobs, {len(cities)} locations). Visa check run {day}. "
         "No job descriptions downloaded, not scored.", "",
         f"**{n_sp} jobs kept** ({counts['yes']} ✅ register / company statement, {n_weak} ⚠️ weak, "
         f"{n_country} 🌍 country rule). {len(gpt)} visa-unclear jobs went to `gpt_automation/company_list.md`; "
         f"{counts['no'] + counts['agency']} dropped (says no / agency).", "",
         "| City | Company sites | LinkedIn |", "|---|---|---|"]
    L += [f"| {c} | {len(sponsor[c]['site'])} | {len(sponsor[c]['li'])} |" for c in cities
          if sponsor[c]["site"] or sponsor[c]["li"]]
    for part, key in (("Company sites", "site"), ("LinkedIn", "li")):
        L += ["", f"# {part}", ""]
        for c in cities:
            if sponsor[c][key]:
                L += [f"## {c} ({len(sponsor[c][key])})", "", H, *sponsor[c][key], ""]
    L += ["", "# Removed - no public visa info", ""]
    for kind, head in (("no", "Says no sponsorship / residents only"),
                       ("agency", "Recruitment agency or job board - the real employer isn't named")):
        L += [f"## {head} ({len(dropped[kind])})", *[f"- {x}" for x in sorted(dropped[kind])], ""]
    out_dir = ROOT / "job_lists" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sponsor_jobs.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # 2. GPT list (visa unclear) - replaces the previous one, copy in archive/
    gpt.sort(key=lambda g: (g[0].lower(), g[2]))
    G = [f"# Company list - run {day} ({a.window}, {len(cities)} locations)", "",
         f"**{len(gpt)} jobs, {len({g[0] for g in gpt})} companies** - visa unclear: no sponsorship evidence found yet. "
         "Evidence so far = what was checked (column 5). Links are the original postings.", "",
         "| Company | Job | City | Source | What was checked | Link |", "|---|---|---|---|---|---|"]
    G += [f"| {c} | {j} | {ci} | {s} | {w} | {u} |" for c, j, ci, s, w, u in gpt]
    G += ["", "## Not for processing (dropped)", ""]
    G += [f"- {x} - says no sponsorship" for x in sorted(dropped["no"])]
    G += [f"- {x} - recruitment agency" for x in sorted(dropped["agency"])]
    (GPT / "archive").mkdir(parents=True, exist_ok=True)
    text = "\n".join(G) + "\n"
    (GPT / "company_list.md").write_text(text, encoding="utf-8")
    (GPT / "archive" / f"company_list_{day}.md").write_text(text, encoding="utf-8")
    old = GPT / "company_list.txt"
    if old.exists():   # the old plain-text format; earlier runs are in archive/
        old.unlink()

    print(f"{sum(counts.values())} jobs: {n_sp} sponsor ({counts['yes']} yes, {n_weak} weak, {n_country} country rule), "
          f"{len(gpt)} unclear -> GPT, {counts['no']} says no, {counts['agency']} agency")
    print(f"Saved {out_dir / 'sponsor_jobs.md'} and {GPT / 'company_list.md'}")


if __name__ == "__main__":
    main()
