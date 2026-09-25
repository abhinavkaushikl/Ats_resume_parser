#!/usr/bin/env python3
"""
sponsor_registers.py - check companies against visa-sponsor lists, no LLM and no web search.

Official registers (strong evidence) - downloaded to jobs/registers/, refreshed when older than 7 days:
  UK  Home Office register of licensed sponsors (workers)         -> London
  NL  IND public register of recognised sponsors                  -> Amsterdam
  DK  SIRI fast-track scheme certified companies                  -> Copenhagen
Employer lists (weak evidence - Germany and Spain have no sponsor register, any employer can hire on a
Blue Card, so these are public lists of employers known to sponsor / relocate):
  DE  Relocate.me employers hiring in Germany (every listing offers visa + relocation), Arbeitnow job ads
      whose own text offers visa sponsorship, and the community list SiaExplains/visa-sponsorship-companies
                                                                   -> Berlin, Munich
  ES  Relocate.me employers hiring in Spain + the community list  -> Barcelona

For a job list (jobs/jobs_<date>_<HHMM>.md from step 1) it matches every company in those cities, saves
each hit to jobs/visa_companies.json (register hits as official, list hits as weak) so step 2 only
researches the rest, and writes jobs/register_hits_<date>.json.

Match types
  exact      - the company name (minus legal suffixes) equals a listed name
  candidate  - a listed name starts with the company's first word ("Amazon Science" -> "Amazon UK
               Services Ltd"): confirm by eye / one search, then decide
  none       - not listed. In the UK that usually means no Skilled Worker sponsorship, but the legal
               entity name can differ; in Germany / Spain it means nothing - research as usual

Usage
  .venv/bin/python sponsor_registers.py jobs/jobs_2026-09-26_0700.md
  .venv/bin/python sponsor_registers.py --refresh                      # re-download everything now
  .venv/bin/python sponsor_registers.py --check "HelloFresh" Berlin
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
REG = JOBS / "registers"
MAX_AGE_DAYS = 7
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"}
GITHUB = "https://raw.githubusercontent.com/SiaExplains/visa-sponsorship-companies/main/countries/{}.json"
RELOCATE = "https://relocate.me/companies-hiring/{}"
ARBEITNOW = "https://www.arbeitnow.com/api/job-board-api?page={}"

REGISTERS = {
    "UK": {"official": True, "label": "UK sponsor register", "cities": {"London"}, "country": "UK",
           "page": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"},
    "NL": {"official": True, "label": "IND recognised sponsor", "cities": {"Amsterdam"}, "country": "Netherlands",
           "page": "https://ind.nl/en/public-register-recognised-sponsors/"
                   "public-register-regular-labour-and-highly-skilled-migrants"},
    "DK": {"official": True, "label": "SIRI fast-track certified", "cities": {"Copenhagen"}, "country": "Denmark",
           "page": "https://www.nyidanmark.dk/en-GB/Words%20and%20Concepts%20Front%20Page/SIRI/Certified%20companies"},
    "DE": {"official": False, "label": "known sponsor list (Germany)", "cities": {"Berlin", "Munich"},
           "country": "Germany", "slug": "germany"},
    "ES": {"official": False, "label": "known sponsor list (Spain)", "cities": {"Barcelona"},
           "country": "Spain", "slug": "spain"},
}
SUFFIX = re.compile(r"\b(ltd|limited|plc|llp|lp|inc|incorporated|corp|corporation|co|company|gmbh|mbh|ag|se|sa|"
                    r"sas|sl|slu|bv|b v|nv|n v|a s|as|aps|ab|oy|srl|spa|kg|holding|holdings|group|uk|"
                    r"international|t a|germany|deutschland|spain|espana|danmark|denmark)\b")
VISA_YES = re.compile(r"visa\s+sponsor|sponsor(ship|ing)?\s+(of\s+)?(your\s+|a\s+|the\s+)?(work\s+)?(visa|permit)|"
                      r"(visa|work permit|blue card)\s+(support|assistance|process|application|help)|"
                      r"relocation\s+(and|&)\s+visa|visa\s+(and|&)\s+relocation", re.I)
VISA_NO = re.compile(r"(no|not|cannot|can't|unable to|do not|don't|without)\s+(\w+\s+){0,3}(visa\s+)?sponsor|"
                     r"must (already )?have (the )?(right|permission) to work|keine\s+(visa|visum)", re.I)


def norm(name: str) -> str:
    s = name.lower().replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()  # Rambøll -> ramboll, é -> e
    s = s.replace("&", " and ").replace("®", " ").replace("™", " ").replace("-", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _get(url: str, timeout: int = 60) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def _html_names(text: str) -> list[str]:
    """Registered names from an HTML table page (IND, SIRI)."""
    out = set()
    for c in re.findall(r"<(?:td|li|th)[^>]*>(.*?)</(?:td|li|th)>", text, flags=re.S | re.I):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
        if 2 < len(t) < 120 and re.search(r"[A-Za-z]", t) and not re.fullmatch(r"[\d\s./-]+", t):
            out.add(t)
    return sorted(out)


COUNTRY_SLUGS = {"australia", "austria", "belgium", "canada", "croatia", "cyprus", "czech-republic", "denmark",
                 "estonia", "finland", "france", "germany", "ireland", "italy", "japan", "latvia", "lithuania",
                 "luxembourg", "malta", "netherlands", "new-zealand", "norway", "poland", "portugal", "singapore",
                 "spain", "sweden", "switzerland", "united-arab-emirates", "united-kingdom", "united-states"}


def _relocate(slug: str) -> list[tuple[str, str]]:
    """Employers on Relocate.me's 'companies hiring in <country>' page (every listing offers visa + relocation)."""
    links = set(re.findall(r'href="/companies-hiring/([a-z0-9-]+)"', _get(RELOCATE.format(slug)).text))
    return [(c.replace("-", " "), f"https://relocate.me/companies-hiring/{c}") for c in sorted(links - COUNTRY_SLUGS)]


def _github(slug: str) -> list[tuple[str, str]]:
    url = GITHUB.format(slug)
    return [(x["name"], f"https://github.com/SiaExplains/visa-sponsorship-companies/blob/main/countries/{slug}.json")
            for x in _get(url).json() if x.get("name")]


def _arbeitnow(pages: int = 10) -> list[tuple[str, str]]:
    """German job ads whose own text offers visa sponsorship (and doesn't say it can't)."""
    out = {}
    for p in range(1, pages + 1):
        try:
            data = _get(ARBEITNOW.format(p)).json().get("data", [])
        except Exception:
            break
        for j in data:
            text = re.sub(r"<[^>]+>", " ", j.get("description", ""))
            if VISA_YES.search(text) and not VISA_NO.search(text):
                out.setdefault(j["company_name"], j["url"])
        if not data:
            break
        time.sleep(1)
    return sorted(out.items())


def download(key: str) -> list[tuple[str, str]]:
    reg = REGISTERS[key]
    if key == "UK":
        page = _get(reg["page"]).text
        csv_url = re.search(r"https://assets\.publishing\.service\.gov\.uk/[^\"']+\.csv", page).group(0)
        rows = _get(csv_url, timeout=180).text.splitlines()[1:]
        entries = [(r[0].strip(), reg["page"]) for r in csv.reader(rows) if r and r[0].strip()]
    elif reg["official"]:
        entries = [(n, reg["page"]) for n in _html_names(_get(reg["page"]).text)]
    else:
        entries = []
        for fetch in (lambda: _relocate(reg["slug"]), lambda: _github(reg["slug"]),
                      lambda: _arbeitnow() if key == "DE" else []):
            try:
                entries += fetch()
            except Exception as exc:
                print(f"{key}: one source failed ({exc})")
    entries = sorted(dict(entries).items())
    if len(entries) < (100 if reg["official"] else 5):
        raise RuntimeError(f"{key} list looks wrong ({len(entries)} names) - page layout changed?")
    REG.mkdir(parents=True, exist_ok=True)
    lines = [n if reg["official"] else f"{n}\t{s}" for n, s in entries]  # registers: the page is the source
    (REG / f"{key}.tsv").write_text("\n".join(lines), encoding="utf-8")
    return entries


def load(key: str, refresh: bool = False) -> list[tuple[str, str]]:
    f = REG / f"{key}.tsv"
    fresh = f.exists() and time.time() - f.stat().st_mtime < MAX_AGE_DAYS * 86400
    if refresh or not fresh:
        try:
            entries = download(key)
            print(f"{key}: downloaded {len(entries)} names")
            return entries
        except Exception as exc:
            if not f.exists():
                raise
            print(f"{key}: download failed ({exc}); using the saved copy")
    page = REGISTERS[key].get("page", "")
    return [tuple(l.split("\t", 1)) if "\t" in l else (l, page)
            for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


_INDEX: dict[str, dict[str, list[tuple[str, str]]]] = {}


def index(key: str) -> dict[str, list[tuple[str, str]]]:
    if key not in _INDEX:
        idx: dict[str, list[tuple[str, str]]] = {}
        for name, src in load(key):
            idx.setdefault(norm(name), []).append((name, src))
        _INDEX[key] = idx
    return _INDEX[key]


def check(company: str, city: str) -> dict | None:
    """{register, official, match: exact|candidate|none, names, source} for a company, else None."""
    key = next((k for k, r in REGISTERS.items() if city in r["cities"]), None)
    if not key:
        return None
    reg, idx, c = REGISTERS[key], index(key), norm(company)
    res = {"register": key, "official": reg["official"], "label": reg["label"], "match": "none", "names": [],
           "source": reg.get("page", "")}
    if not c:
        return res
    if c in idx:
        return {**res, "match": "exact", "names": [n for n, _ in idx[c][:3]], "source": idx[c][0][1]}
    first = c.split()[0]
    cands = [(n, s) for k, v in idx.items() if k == first or k.startswith(first + " ") for n, s in v]
    if len(first) >= 3 and cands:
        return {**res, "match": "candidate", "names": [n for n, _ in cands[:5]], "source": cands[0][1]}
    return res


def parse_jobs(path: Path) -> list[tuple[str, str]]:
    """(city, company) pairs from a job-list / visa file (## <City> (n) headings, table rows)."""
    pairs, city = [], ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Removed"):
            break
        if m := re.match(r"## (\w+) \(", line):
            city = m.group(1)
        if line.startswith("| ") and "](" in line:
            pairs.append((city, line.split(" | ")[2].strip()))
    return list(dict.fromkeys(pairs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job_list", nargs="?", help="jobs/jobs_<date>_<HHMM>.md")
    ap.add_argument("--refresh", action="store_true", help="re-download every list now")
    ap.add_argument("--check", nargs=2, metavar=("COMPANY", "CITY"))
    a = ap.parse_args()
    if a.refresh:
        for k in REGISTERS:
            load(k, refresh=True)
    if a.check:
        print(json.dumps(check(*a.check), indent=1, ensure_ascii=False))
    if not a.job_list:
        return

    cache_f = JOBS / "visa_companies.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    hits, counts = [], {}
    for city, company in parse_jobs(Path(a.job_list)):
        r = check(company, city)
        if not r:
            continue
        hits.append({"company": company, "city": city, **r})
        counts.setdefault(r["register"], {"exact": 0, "candidate": 0, "none": 0})[r["match"]] += 1
        if r["match"] == "exact":
            cache[f"{company}|{REGISTERS[r['register']]['country']}"] = {
                "visa": "yes" if r["official"] else "weak", "relocation": "", "src": r["source"],
                "official": r["official"], "register": r["label"], "checked": now}
    cache_f.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    date = re.search(r"\d{4}-\d{2}-\d{2}", Path(a.job_list).name)
    out = JOBS / f"register_hits_{date.group(0) if date else datetime.now().strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(hits, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, c in counts.items():
        kind = "official register" if REGISTERS[k]["official"] else "employer list (weak)"
        print(f"{k} ({kind}): {c['exact']} listed, {c['candidate']} to confirm (similar name), {c['none']} not listed")
    print(f"Saved {out.relative_to(ROOT)}; listed companies cached in jobs/visa_companies.json")


if __name__ == "__main__":
    main()
