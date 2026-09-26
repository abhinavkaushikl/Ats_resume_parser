#!/usr/bin/env python3
"""
jd_extractor.py - one Markdown file per job with the full job description, for every job kept by the
visa-sponsorship check (jobs/*_visa.md).

For each job it takes the company name and job title, finds the posting on the company's career site or
its ATS (Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Personio, ...), opens it with Playwright (a
real headless browser, so JavaScript career pages work) and saves the description. A page is accepted only
if it shows the job title and a real description.

If the company site has nothing and the job is a LinkedIn listing, the description is read from LinkedIn's
public job page - no login, no account involved - slowly (a few seconds between requests). If LinkedIn
rate-limits (HTTP 429) twice, the LinkedIn fallback is switched off for the rest of the run.
Turn it off with --no-linkedin.

Output
  jobs/jd_visa/<date>/<Company>_<Title>.md   one file per role
  jobs/jd_visa/<date>/skipped/<...>.md       JDs that match the base resume below 60% (job_match.py)
  jobs/jd_visa/<date>/README.md              index: shortlisted / skipped / not found, with match and source

Usage
  .venv/bin/python jd_extractor.py                                   # latest jobs/*_visa.md
  .venv/bin/python jd_extractor.py jobs/jobs_2026-09-25_0014_visa.md
  .venv/bin/python jd_extractor.py --limit 5                         # quick test
  .venv/bin/python jd_extractor.py --min-match 70                    # stricter resume match (default 60)
  .venv/bin/python jd_extractor.py --no-linkedin                     # company sites only
"""
from __future__ import annotations

import argparse
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from ddgs import DDGS
from markdownify import markdownify
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from job_match import MIN_MATCH, match_lines
from job_match import score as match_score

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"

# Never used as the JD source: LinkedIn, and aggregators that copy postings (often truncated or stale).
BLOCKED = ("linkedin.", "indeed.", "glassdoor.", "ziprecruiter.", "jooble.", "jaabz.", "arbeitnow.", "themuse.",
           "builtin.", "relocate.me", "talent.com", "simplyhired.", "monster.", "stepstone.", "xing.", "jobgether.",
           "eurobrussels.", "welcometothejungle.", "freehire.", "remocate.", "efinancialcareers.", "adzuna.",
           "careerjet.", "jobleads.", "whatjobs.", "totaljobs.", "reed.co.uk", "cv-library.", "hisignal.",
           "englishjobs.", "visajobs", "huntukvisasponsors.", "facebook.", "instagram.", "youtube.", "wikipedia.")
ATS = ("greenhouse.io", "lever.co", "ashbyhq.com", "smartrecruiters.com", "workable.com", "personio.",
       "recruitee.com", "myworkdayjobs.com", "successfactors.", "teamtailor.com", "join.com", "bamboohr.com",
       "jobvite.com", "icims.com", "taleo.net", "eightfold.ai", "phenompeople.com", "oraclecloud.com",
       "pinpointhq.com", "firststage.co", "amazon.jobs", "metacareers.com", "careers.google.com", "google.com/about/careers")
GONE = re.compile(r"no longer (available|accepting|open)|position (has been )?(filled|closed)|job (is )?(closed|expired)|"
                  r"page (not|could not be) found|404|diese stelle ist nicht mehr", re.I)
STOP = {"m", "w", "d", "f", "x", "all", "genders", "gn", "div", "h", "the", "and", "for", "of", "in", "with", "a",
        "an", "to", "senior", "junior", "sr", "mid", "lead", "remote", "hybrid", "london", "paris", "berlin",
        "munich", "münchen", "amsterdam", "warsaw", "bucharest", "copenhagen", "vienna", "oslo", "emea"}


@dataclass
class Job:
    city: str
    company: str
    title: str
    url: str
    visa: str


def visa_unsure(visa_cell: str) -> bool:
    """Unclear visa - no evidence at all. Weak (⚠️) evidence still counts as a yes and is processed."""
    v = visa_cell.lower()
    return "unclear" in v or not v.startswith("visa: yes")


def parse_visa_file(path: Path) -> list[Job]:
    jobs, city = [], ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Removed"):
            break
        if m := re.match(r"## (\w+) \(", line):
            city = m.group(1)
        if line.startswith("| ") and "](" in line:
            c = line.split(" | ")
            t = re.match(r"\[(.*)\]\((.*)\)", c[1].strip())
            jobs.append(Job(city, c[2].strip(), t.group(1), t.group(2), c[6].strip()))
    return jobs


def title_tokens(title: str) -> list[str]:
    return [w for w in re.findall(r"[a-zà-ÿ0-9+#]+", title.lower()) if w not in STOP and len(w) > 1]


def title_match(title: str, text: str) -> float:
    toks = title_tokens(title)
    low = text.lower()
    return sum(t in low for t in toks) / len(toks) if toks else 0.0


def company_keys(company: str) -> set[str]:
    """Strings the company's own domain should contain, e.g. 'Fitch Group, Inc.' -> {'fitch'}."""
    name = re.sub(r"\b(gmbh|ag|se|ltd|limited|inc|plc|bv|sa|group|technologies|poland|polska|romania|deutschland|"
                  r"europe|latam|the|a|an|company|corporate|and|investment|banking|studios)\b\.?", " ",
                  company.lower().split(",")[0].replace("&", " "))
    words = re.findall(r"[a-z0-9]+", name)
    keys = {"".join(words)[:12]} | {w for w in words[:1]}
    return {k for k in keys if len(k) >= 2}


def official(url: str, company: str) -> bool:
    """The company's own site or a known ATS - not an aggregator that copies postings."""
    host = urlparse(url).netloc.lower()
    if any(b in host for b in BLOCKED):
        return False
    if any(a in url for a in ATS):
        return True
    flat, parts = re.sub(r"[^a-z0-9]", "", host), set(re.split(r"[.\-]", host))
    return any((len(k) >= 4 and k in flat) or k in parts for k in company_keys(company))


CITY_WORDS = {
    "Berlin": ["berlin", "germany", "deutschland"], "Munich": ["munich", "münchen", "muenchen", "germany", "deutschland"],
    "Amsterdam": ["amsterdam", "netherlands", "nederland"], "Brussels": ["brussels", "bruxelles", "brussel", "belgium"],
    "Paris": ["paris", "france", "île-de-france"], "Copenhagen": ["copenhagen", "københavn", "denmark", "danmark"],
    "Warsaw": ["warsaw", "warszawa", "poland", "polska"], "London": ["london", "united kingdom", " uk"],
    "Austria": ["austria", "österreich", "vienna", "wien", "graz", "linz", "villach"],
    "Romania": ["romania", "românia", "bucharest", "bucurești", "bucuresti", "cluj", "iasi", "iași", "timisoara"],
    "Norway": ["norway", "norge", "oslo", "bergen", "trondheim"],
    "Barcelona": ["barcelona", "spain", "españa", "catalonia", "cataluña", "catalunya"]}


def right_place(city: str, text: str, url: str) -> bool:
    low = f"{text} {url}".lower()
    return any(w in low for w in CITY_WORDS.get(city, [city.lower()]))


def search(job: Job) -> list[str]:
    """Candidate posting URLs from web search, best first: company site or ATS only, never LinkedIn."""
    queries = [f'"{job.company}" "{job.title}"', f"{job.company} {job.title} careers apply",
               f"{job.company} {job.title} {job.city} job"]
    seen, ranked = set(), []
    for q in queries:
        for backend in ("bing", "duckduckgo"):
            try:
                res = DDGS().text(q + " -site:linkedin.com", max_results=10, backend=backend)
            except Exception:
                continue
            for r in res:
                url = r.get("href", "")
                if not url or url in seen or not official(url, job.company):
                    continue
                seen.add(url)
                score = title_match(job.title, f"{r.get('title', '')} {r.get('body', '')}")
                score += 1.0 if urlparse(url).path.strip("/") else 0     # a posting, not a homepage
                ranked.append((score, url))
            time.sleep(random.uniform(1.5, 3))
            if ranked:
                break
        if any(s >= 1.5 for s, _ in ranked):
            break
    return [u for s, u in sorted(ranked, reverse=True) if s >= 0.5][:4]


EXTRACT_JS = """() => {
  const pageText = document.body.innerText, bodyLen = pageText.length;
  const sel = ['[data-automation-id="jobPostingDescription"]', '.job-description', '#job-description',
    '[class*="jobDescription"]', '[class*="job-description"]', '[class*="posting"]', '[class*="description"]',
    'article', 'main', '[role="main"]', '#content', '.content'];
  let best = null, bestLen = 0;
  for (const s of sel) for (const el of document.querySelectorAll(s)) {
    const n = el.innerText.length;
    if (n > bestLen && n > 400 && n <= bodyLen) { best = el; bestLen = n; }
  }
  best = best || document.body;
  best.querySelectorAll('script,style,nav,footer,header,form,button,svg,iframe,noscript').forEach(e => e.remove());
  return {html: best.innerHTML, text: best.innerText, title: document.title, page: pageText};
}"""


def fetch(page, url: str) -> dict | None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PWTimeout:
            pass
        for label in ("Accept all", "Accept", "Alle akzeptieren", "Tout accepter", "I agree", "Allow all"):
            btn = page.get_by_role("button", name=label, exact=True)
            if btn.count():
                try:
                    btn.first.click(timeout=2000)
                    break
                except Exception:
                    pass
        return page.evaluate(EXTRACT_JS)
    except Exception:
        return None


class LinkedInLimited(Exception):
    pass


def linkedin_jd(url: str) -> str | None:
    """The description from LinkedIn's public (logged-out) job page, as Markdown; None if there is none."""
    job_id = re.search(r"(\d{6,})/?(?:\?.*)?$", url)
    if not job_id:
        return None
    r = requests.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id.group(1)}", timeout=30,
                     headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                            "(KHTML, like Gecko) Chrome/140.0 Safari/537.36",
                              "Accept-Language": "en-GB,en;q=0.9"})
    if r.status_code == 429:
        raise LinkedInLimited()
    if r.status_code != 200:
        return None
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', r.text, re.S)
    md = clean_md(m.group(1)) if m else ""
    return md if len(md) >= 300 else None


def clean_md(html: str) -> str:
    md = markdownify(html, heading_style="ATX", strip=["a", "img"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    return "\n".join(l.rstrip() for l in md.splitlines()).strip()


def slug(s: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]+", "_", s)).strip("_")[:70]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("visa_file", nargs="?", help="jobs/*_visa.md (default: newest)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-match", type=int, default=MIN_MATCH, help="resume match %% to shortlist (default 60)")
    ap.add_argument("--no-match", action="store_true",
                    help="only extract JDs; score them later with: job_match.py jobs/jd_visa/<date>")
    ap.add_argument("--no-linkedin", action="store_true", help="never fall back to LinkedIn's public job page")
    ap.add_argument("--only", nargs="+", metavar="TEXT",
                    help="process only jobs whose 'company title city' contains one of these (any visa status) - "
                         "for the visa-unsure jobs I pick after reviewing them")
    a = ap.parse_args()
    src = Path(a.visa_file) if a.visa_file else max(JOBS.glob("*_visa.md"), key=lambda p: p.stat().st_mtime)
    jobs = parse_visa_file(src)
    if a.only:
        jobs = [j for j in jobs if any(t.lower() in f"{j.company} {j.title} {j.city}".lower() for t in a.only)]
    else:
        # My rule: visa-unclear jobs are not extracted, scored or tailored - they go to GPT
        # (gpt_automation/company_list.txt). Weak-evidence jobs are processed like confirmed ones.
        unsure = [j for j in jobs if visa_unsure(j.visa)]
        jobs = [j for j in jobs if not visa_unsure(j.visa)]
        if unsure:
            print(f"{len(unsure)} visa-unclear jobs skipped (they go to GPT; process one here with --only)")
    jobs = jobs[: a.limit or None]
    out = JOBS / "jd_visa" / datetime.now().strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(jobs)} jobs from {src.name} -> {out}")

    rows, use_linkedin, li_limited = [], not a.no_linkedin, 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="en-GB", viewport={"width": 1366, "height": 900}, user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"))
        page = ctx.new_page()
        for i, job in enumerate(jobs, 1):
            direct = [] if "linkedin." in job.url else [job.url]
            found, tried = None, 0
            for url in direct + [u for u in search(job) if u not in direct]:
                tried += 1
                got = fetch(page, url)
                if not got or len(got["text"]) < 800:
                    continue
                # The role must be the page's subject (page title or its opening lines), not one row of a job
                # list, and the posting must be for this job's city / country.
                head = max(title_match(job.title, got["title"]), title_match(job.title, got["text"][:800]))
                if GONE.search(got["text"][:1500]) or head < 0.7 or (
                        url != job.url and not right_place(job.city, f'{got["title"]} {got["page"]}', url)):
                    continue
                found = (url, clean_md(got["html"]))
                break
            if not found and use_linkedin and "linkedin." in job.url:
                time.sleep(random.uniform(3, 6))  # slow and polite: public page, no login
                try:
                    if md := linkedin_jd(job.url):
                        found = (job.url, md)
                except LinkedInLimited:
                    li_limited += 1
                    print(f"  LinkedIn rate limit ({li_limited})", flush=True)
                    if li_limited >= 2:
                        use_linkedin = False
                        print("  LinkedIn fallback off for the rest of this run", flush=True)
                    else:
                        time.sleep(90)
                except requests.RequestException:
                    pass
            name = f"{slug(job.company)}_{slug(job.title)}_{job.city}.md"
            if found:
                url, md = found
                try:
                    m = None if a.no_match else match_score(md)
                except Exception as exc:  # LLM down: keep the JD, unscored
                    print(f"  match not scored: {exc}", flush=True)
                    m = None
                keep = m is None or m.score >= a.min_match
                dest = out if keep else out / "skipped"
                dest.mkdir(exist_ok=True)
                (dest / name).write_text("\n".join([
                    f"# {job.title}", "",
                    f"- **Company:** {job.company}", f"- **City:** {job.city}",
                    f"- **Visa / relocation:** {job.visa}",
                    f"- **Original listing:** {job.url}", f"- **JD source (Playwright):** {url}",
                    f"- **Fetched:** {datetime.now():%Y-%m-%d %H:%M}",
                    *(match_lines(m, a.min_match) if m else ["- **Resume match:** not scored"]),
                    "", "## Job description", "", md, ""]),
                    encoding="utf-8")
                rel = name if keep else f"skipped/{name}"
                pct = f"{m.score}%" if m else "?"
                rows.append((job, "✅" if keep else "⏭", f"{pct} [{name}]({rel})", url))
            else:
                rows.append((job, "❌", f"not found ({tried} pages tried)", ""))
            print(f"[{i}/{len(jobs)}] {rows[-1][1]} {job.company} - {job.title}", flush=True)
        browser.close()

    ok = sum(r[1] == "✅" for r in rows)
    low = sum(r[1] == "⏭" for r in rows)
    L = [f"# Job descriptions - {src.name}", "",
         f"{ok + low} of {len(rows)} found outside LinkedIn and saved, one file per role. "
         f"{ok} shortlisted (resume match {a.min_match}%+), {low} skipped (below {a.min_match}%, in skipped/). "
         f"Fetched with Playwright {datetime.now():%Y-%m-%d %H:%M}.", "",
         "| | City | Company | Title | Match / file | JD source |", "|---|---|---|---|---|---|"]
    for job, mark, f, url in rows:
        L.append(f"| {mark} | {job.city} | {job.company} | {job.title} | {f} | {url} |")
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{ok} shortlisted, {low} skipped (< {a.min_match}%), {len(rows) - ok - low} not found. Index: {out / 'README.md'}")


if __name__ == "__main__":
    main()
