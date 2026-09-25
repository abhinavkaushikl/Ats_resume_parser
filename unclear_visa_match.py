#!/usr/bin/env python3
"""
unclear_visa_match.py - the job list for companies whose visa status stayed unclear, so they get the same
processing as the visa-confirmed jobs: full job description, resume match, and - at 60%+ - a place in the
results (flagged "visa unclear, confirm with recruiter").

"Unclear" means: removed by the visa check only because no public visa info was found (not because the
company said no, and not a recruitment agency), and - if jobs/visa_research_<date>.json exists - still
"unclear" after the deeper research.

Output
  jobs/unclear_<date>.md   same table format as *_visa.md, visa cell "Visa: unclear ..."
Then run
  .venv/bin/python jd_extractor.py jobs/unclear_<date>.md

Usage
  .venv/bin/python unclear_visa_match.py                                   # newest jobs/*_visa.md
  .venv/bin/python unclear_visa_match.py jobs/jobs_2026-09-25_0014_visa.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
VISA_CELL = "Visa: unclear - no public info found · confirm with recruiter before applying"


def unclear_companies(visa_file: Path, date: str) -> set[tuple[str, str]]:
    """(company, city) pairs whose visa status is still unclear."""
    research = JOBS / f"visa_research_{date}.json"
    if research.exists():
        return {(r["company"], r["city"]) for r in json.loads(research.read_text(encoding="utf-8"))
                if r["verdict"] == "unclear"}
    visa = visa_file.read_text(encoding="utf-8")
    if "## No public visa-sponsorship info found" not in visa:
        return set()
    return {(m.group(1).strip(), m.group(2))
            for line in visa.split("## No public visa-sponsorship info found", 1)[1].splitlines()
            if (m := re.match(r"- (.+) \((\w+)\)$", line.strip()))}


def source_file(visa_file: Path) -> Path:
    src = re.search(r"Source list: (\S+\.md)", visa_file.read_text(encoding="utf-8"))
    return JOBS / (src.group(1) if src else visa_file.name.replace("_visa.md", ".md"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("visa_file", nargs="?", type=Path, help="jobs/*_visa.md (default: newest)")
    a = ap.parse_args()
    visa_file = a.visa_file or max(JOBS.glob("*_visa.md"), key=lambda p: p.stat().st_mtime)
    date = re.search(r"(\d{4}-\d{2}-\d{2})", visa_file.name).group(1)
    unclear = unclear_companies(visa_file, date)

    by_city, city = {}, None
    for line in source_file(visa_file).read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## (\w+) \(", line):
            city = m.group(1)
        if line.startswith("| ") and "](" in line:
            cells = line.split(" | ")
            if (cells[2].strip(), city) in unclear:
                cells[6] = VISA_CELL
                by_city.setdefault(city, []).append(" | ".join(cells))

    L = [f"# Jobs with unclear visa status - {date}", "",
         f"Source list: {source_file(visa_file).name}. Companies with no public visa info after the visa check"
         " and deeper research. Processed like the other jobs; confirm visa with the recruiter.", ""]
    for c, rows in by_city.items():
        L += [f"## {c} ({len(rows)})", "", "| | Title | Company | Level | Location | Opened | Visa / Relocation | JD | Source |",
              "|---|---|---|---|---|---|---|---|---|", *rows, ""]
    out = JOBS / f"unclear_{date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    n = sum(len(r) for r in by_city.values())
    print(f"{n} unclear-visa jobs from {len(unclear)} companies -> {out}\n"
          f"Next: .venv/bin/python jd_extractor.py {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
