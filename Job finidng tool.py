#!/usr/bin/env python3
"""
job_hunter.py - find fresh AI / ML / data-science jobs on company career portals and
save them as Markdown. No company list needed.

How it works
  1. DISCOVER  Runs Google searches restricted to the past 24 hours on every career-portal
               site (Greenhouse, Lever, Ashby, Workable, Personio, SmartRecruiters, Recruitee,
               Teamtailor, Workday, Join) and on XING Jobs for every city, via a search API.
  2. VERIFY    For each company found on a portal with a public job feed, it downloads that
               company's full feed to get the real posting date, exact location - and any
               other matching jobs at the same company.
     For XING and portals without a feed, it reads the job page's structured
               data (schema.org JobPosting) to get the real date, company and location.
  3. REMEMBER  Every company it finds is saved to jobs/discovered_companies.yaml and checked
               directly on every future run, so coverage grows by itself.
  4. SCREEN    Optional Claude pass drops irrelevant postings and tags level + focus.
  4b. VISA     Marks visa sponsorship and relocation support per job: first from the job description
               ("visa sponsorship", "relocation package", "no sponsorship", "must have the right to
               work"), then, where the JD is silent, one web search per company (cached 30 days in
               jobs/visa_companies.json; VISA_WEB_LIMIT new companies per run, default 25;
               VISA_SEARCH_DELAY seconds between free Bing searches, default 10). --no-visa-check skips it.
  5. WRITE     jobs/latest.md (+ a timestamped copy): company career sites and LinkedIn in separate
               parts, grouped by city, new jobs marked 🆕, with a Visa / Relocation column.

Search backend (first one configured wins)
  Serper.dev  (2,500 free searches):        SERPER_API_KEY
  Google Programmable Search (100/day free): GOOGLE_API_KEY + GOOGLE_CSE_ID
  Bing (free, no key - default):             slow and paced (BING_DELAY seconds between searches);
                                             no date filter, so dates come from the company feeds

Usage
  python job_hunter.py                 # last 24h, all cities
  python job_hunter.py --hours 72
  python job_hunter.py --senior-only
  python job_hunter.py --claude        # needs ANTHROPIC_API_KEY
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import requests
import yaml

# ==========================================================================
# Configuration - edit freely
# ==========================================================================

# City -> (term used in the Google query, words that identify it in a job location)
CITIES: dict[str, tuple[str, list[str]]] = {
    "Berlin":     ("Berlin", ["berlin"]),
    "Munich":     ("(Munich OR München)", ["munich", "münchen", "muenchen"]),
    "Amsterdam":  ("Amsterdam", ["amsterdam"]),
    "Brussels":   ("(Brussels OR Bruxelles)", ["brussels", "bruxelles", "brussel"]),
    "Paris":      ("Paris", ["paris", "île-de-france", "ile-de-france"]),
    "Copenhagen": ("(Copenhagen OR København)", ["copenhagen", "københavn", "kobenhavn", "herlev", "lyngby"]),
    "Warsaw":     ("(Warsaw OR Warszawa)", ["warsaw", "warszawa"]),
    "Austria":    ("(Vienna OR Wien OR Austria)", ["austria", "österreich", "vienna", "wien", "graz", "linz", "salzburg", "innsbruck"]),
    "London":     ("London", ["london"]),
    "Romania":    ("(Romania OR Bucharest OR București)", ["romania", "românia", "bucharest", "bucurești", "bucuresti", "cluj", "iași", "timișoara", "timisoara", "brașov", "brasov"]),
    "Norway":     ("(Norway OR Oslo OR Norge)", ["norway", "norge", "oslo", "bergen", "trondheim", "stavanger"]),
    "Barcelona":  ("Barcelona", ["barcelona", "catalonia", "cataluña", "catalunya"]),
}

# Career-portal sites searched on Google.
PORTAL_SITES = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "personio.de",
    "smartrecruiters.com", "recruitee.com", "teamtailor.com", "myworkdayjobs.com", "join.com",
    "xing.com/jobs",
]
# XING is mostly German-speaking; searching it elsewhere wastes API credits.
# Use --xing-all-cities to search XING for every city.
XING_CITIES = {"Berlin", "Munich", "Austria"}
SOURCE_NAMES = {"xing.com": "XING", "teamtailor.com": "Teamtailor", "myworkdayjobs.com": "Workday",
                "join.com": "Join"}

# Titles put into the Google query. Long lists are split automatically into
# several queries, because Google ignores words beyond ~32.
SEARCH_TITLES = [
    "data scientist", "data science", "machine learning", "ML engineer", "AI engineer",
    "artificial intelligence", "applied scientist", "research scientist", "MLOps",
    "GenAI", "generative AI", "LLM", "NLP", "computer vision", "deep learning",
    "AI developer", "AI specialist", "AI consultant", "forward deployed",
]

# Final title filter: must match one of these ...
TITLE_PATTERNS = [
    r"data scien", r"machine learning", r"\bml\b", r"\bmlops\b",
    r"\bai\b", r"artificial intelligence", r"\bk[iü]\b",
    r"applied scientist", r"research scientist", r"research engineer",
    r"\bllm", r"gen ?ai", r"generative", r"\bnlp\b", r"computer vision",
    r"deep learning", r"forward[- ]deployed", r"\bfde\b",
]
# ... and none of these.
EXCLUDE_PATTERNS = [
    r"sales", r"account executive", r"recruit", r"talent", r"marketing manager",
    r"legal", r"counsel", r"finance", r"\btutor\b",
]
SENIOR_RE = r"\b(senior|sr\.?|lead|staff|principal|head|director|manager|vp)\b"
JUNIOR_RE = r"\b(junior|jr\.?|intern|internship|werkstudent|working student|praktikum|trainee|graduate|stage|alternance)\b"

HEADERS = {"User-Agent": "job-hunter/2.0 (personal job search script)"}
TIMEOUT = 20

# ==========================================================================
# Data model & helpers
# ==========================================================================

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    posted: datetime | None
    city: str = ""
    level: str = ""
    note: str = ""
    verified: bool = True
    slug: str = ""          # company's board name on its portal (used to fetch the full JD)
    visa: str = ""          # visa sponsorship: "yes" / "no" / "" (unknown), see check_visa_relocation
    relocation: str = ""    # relocation support: "yes" / "no" / ""
    visa_src: str = ""      # where `visa` came from: "JD", or the web page of the company's answer
    reloc_src: str = ""     # where `relocation` came from

    def key(self) -> str:
        return self.url.split("?")[0].split("#")[0].rstrip("/").lower()


def parse_date(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s) if ("T" in s or "+" in s) else datetime.fromisoformat(s[:10])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    m = re.match(r"(\d+)\s+(minute|hour|day|week)s?\s+ago", str(value).lower())   # "3 hours ago"
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return datetime.now(timezone.utc) - timedelta(**{unit + "s": n})
    for fmt in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d %H:%M:%S %Z"):
        try:
            return datetime.strptime(str(value), fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def get_json(url: str, **kw):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def words(s: str) -> int:
    return len(re.sub(r'[()"]', " ", s).split())

# ==========================================================================
# 1. DISCOVER - Google search via Serper or Google Programmable Search
# ==========================================================================

def build_queries(cities: list[str], senior_only: bool, xing_all: bool = False) -> list[tuple[str, str]]:
    """Return (city, query) pairs, splitting titles to stay under Google's word limit."""
    out = []
    for city in cities:
        city_term = CITIES[city][0]
        for site in PORTAL_SITES:
            if site.startswith("xing") and not xing_all and city not in XING_CITIES:
                continue
            budget = 32 - 1 - words(city_term) - (1 if senior_only else 0) - 2
            chunk, used = [], 0
            chunks = []
            for t in SEARCH_TITLES:
                cost = words(t) + (1 if chunk else 0)
                if chunk and used + cost > budget:
                    chunks.append(chunk); chunk, used = [], 0
                    cost = words(t)
                chunk.append(t); used += cost
            if chunk:
                chunks.append(chunk)
            for ch in chunks:
                titles = " OR ".join(f'"{t}"' if " " in t else t for t in ch)
                q = f"site:{site} ({titles}) {city_term}" + (" senior" if senior_only else "")
                out.append((city, q))
    return out


def search_serper(query: str, hours: int, key: str) -> list[dict]:
    tbs = "qdr:d" if hours <= 24 else ("qdr:w" if hours <= 168 else "qdr:m")
    results, page = [], 1
    while page <= 3:
        r = requests.post("https://google.serper.dev/search", timeout=TIMEOUT,
                          headers={"X-API-KEY": key, "Content-Type": "application/json"},
                          json={"q": query, "tbs": tbs, "num": 100, "page": page})
        r.raise_for_status()
        organic = r.json().get("organic", [])
        results += [{"url": o.get("link", ""), "title": o.get("title", ""),
                     "date": o.get("date")} for o in organic]
        if len(organic) < 100:
            break
        page += 1
    return results


def search_google_cse(query: str, hours: int, key: str, cx: str) -> list[dict]:
    restrict = f"d{max(1, -(-hours // 24))}"
    results = []
    for start in range(1, 92, 10):                       # CSE returns max 100 results
        r = requests.get("https://www.googleapis.com/customsearch/v1", timeout=TIMEOUT,
                         params={"key": key, "cx": cx, "q": query, "dateRestrict": restrict,
                                 "start": start, "num": 10})
        if r.status_code == 429:
            raise RuntimeError("Google CSE daily quota reached")
        r.raise_for_status()
        items = r.json().get("items", [])
        results += [{"url": i.get("link", ""), "title": i.get("title", ""), "date": None} for i in items]
        if len(items) < 10:
            break
    return results


def search_bing(query: str, delay: float) -> list[dict]:
    """Free Bing search (via the ddgs library). Paced, because Bing throttles fast repeated searches."""
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException
    time.sleep(delay + random.uniform(0, delay / 2))
    for attempt in range(2):
        try:
            res = DDGS().text(query, max_results=50, backend="bing")
            return [{"url": r.get("href", ""), "title": r.get("title", ""), "date": None} for r in res]
        except DDGSException as ex:
            if "no results" in str(ex).lower():
                return []
            if attempt == 0:
                time.sleep(60)                     # throttled: back off once, then give up on this query
            else:
                raise
    return []


def on_portal(url: str) -> bool:
    return any(site in url for site in PORTAL_SITES)


def discover(cities, hours, senior_only, xing_all=False) -> list[tuple[str, dict]]:
    serper = os.environ.get("SERPER_API_KEY")
    gkey, gcx = os.environ.get("GOOGLE_API_KEY"), os.environ.get("GOOGLE_CSE_ID")
    queries = build_queries(cities, senior_only, xing_all)
    if serper:
        run = lambda q: search_serper(q, hours, serper); backend = "Serper"
    elif gkey and gcx:
        run = lambda q: search_google_cse(q, hours, gkey, gcx); backend = "Google CSE"
    else:
        delay = float(os.environ.get("BING_DELAY", 20))
        run = lambda q: search_bing(q, delay); backend = f"Bing (free, ~{delay:.0f}s between searches)"
        # Bing handles "a" OR "b" better than ("a" OR "b").
        queries = [(c, re.sub(r"site:(\S+) \((.*?)\) ", r"site:\1 \2 ", q)) for c, q in queries]
    print(f"Discovering via {backend}: {len(queries)} searches")
    hits = []
    with ThreadPoolExecutor(max_workers=4 if serper else 1) as pool:
        futs = {pool.submit(run, q): (city, q) for city, q in queries}
        for f in as_completed(futs):
            city, q = futs[f]
            try:
                res = [r for r in f.result() if on_portal(r["url"])]   # Bing also returns non-portal pages
                hits += [(city, r) for r in res]
                if res:
                    print(f"  ✓ {len(res):>3}  {q[:95]}")
            except Exception as ex:
                print(f"  ✗ {q[:80]}: {ex}")
    print(f"  {len(hits)} search results")
    return hits

# ==========================================================================
# 2. VERIFY - official public job feeds of each portal
# ==========================================================================

URL_PATTERNS = [
    ("greenhouse",      r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)"),
    ("lever",           r"jobs(?:\.eu)?\.lever\.co/([\w.-]+)"),
    ("ashby",           r"jobs\.ashbyhq\.com/([\w.%-]+)"),
    ("workable",        r"apply\.workable\.com/([\w-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
    ("personio",        r"([\w-]+)\.jobs\.personio\.(?:de|com)"),
    ("recruitee",       r"([\w-]+)\.recruitee\.com"),
]
SKIP_SLUGS = {"embed", "api", "jobs", "o", "v1", "careers", "search", "oneclick-ui"}


def identify(url: str) -> tuple[str, str] | None:
    for ats, pat in URL_PATTERNS:
        m = re.search(pat, url, re.I)
        if m and m.group(1).lower() not in SKIP_SLUGS:
            return ats, m.group(1)
    return None


def fetch_greenhouse(slug, name):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    return [Job(j["title"], name, (j.get("location") or {}).get("name", ""), j["absolute_url"],
                "Greenhouse", parse_date(j.get("first_published") or j.get("updated_at")))
            for j in data.get("jobs", [])]


def fetch_lever(slug, name):
    for host in ("api.lever.co", "api.eu.lever.co"):
        try:
            data = get_json(f"https://{host}/v0/postings/{slug}?mode=json")
        except requests.HTTPError:
            continue
        if data:
            out = []
            for j in data:
                c = j.get("categories") or {}
                locs = [c.get("location") or ""] + (c.get("allLocations") or [])
                out.append(Job(j["text"], name, " / ".join(dict.fromkeys(filter(None, locs))),
                               j["hostedUrl"], "Lever", parse_date(j.get("createdAt"))))
            return out
    raise ValueError("no Lever board")


def fetch_ashby(slug, name):
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        out.append(Job(j["title"], name, " / ".join(filter(None, locs)),
                       j.get("jobUrl") or j.get("applyUrl", ""), "Ashby", parse_date(j.get("publishedAt"))))
    return out


def fetch_smartrecruiters(slug, name):
    out, offset = [], 0
    while offset <= 2000:
        data = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                        params={"limit": 100, "offset": offset})
        for j in data.get("content", []):
            loc = j.get("location") or {}
            out.append(Job(j["name"], (j.get("company") or {}).get("name") or name,
                           ", ".join(filter(None, [loc.get("city"), loc.get("country")])),
                           f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", "SmartRecruiters",
                           parse_date(j.get("releasedDate"))))
        offset += 100
        if offset >= data.get("totalFound", 0):
            break
    return out


def fetch_personio(slug, name):
    for tld in ("de", "com"):
        try:
            r = requests.get(f"https://{slug}.jobs.personio.{tld}/xml", headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception:
            continue
        out = []
        for p in root.iter("position"):
            g = lambda t: (p.findtext(t) or "").strip()
            offices = [g("office")] + [o.text or "" for o in p.findall("additionalOffices/office")]
            out.append(Job(g("name"), name, " / ".join(filter(None, offices)),
                           f"https://{slug}.jobs.personio.{tld}/job/{g('id')}", "Personio",
                           parse_date(g("createdAt"))))
        return out
    raise ValueError("no Personio board")


def fetch_recruitee(slug, name):
    data = get_json(f"https://{slug}.recruitee.com/api/offers/")
    return [Job(j["title"], j.get("company_name") or name,
                ", ".join(filter(None, [j.get("city"), j.get("country")])) or j.get("location", ""),
                j.get("careers_url", ""), "Recruitee", parse_date(j.get("published_at") or j.get("created_at")))
            for j in data.get("offers", [])]


def fetch_workable(slug, name):
    data = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    return [Job(j["title"], data.get("name") or name,
                ", ".join(filter(None, [j.get("city"), j.get("country")])),
                j.get("url") or j.get("shortlink", ""), "Workable",
                parse_date(j.get("published_on") or j.get("created_at")))
            for j in data.get("jobs", [])]


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
            "smartrecruiters": fetch_smartrecruiters, "personio": fetch_personio,
            "recruitee": fetch_recruitee, "workable": fetch_workable}


def fetch_feeds(companies: set[tuple[str, str]]) -> tuple[list[Job], set[tuple[str, str]], list[str]]:
    jobs, ok, errors = [], set(), []
    print(f"Verifying {len(companies)} company feeds")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(FETCHERS[a], s, s): (a, s) for a, s in companies}
        for f in as_completed(futs):
            a, s = futs[f]
            try:
                got = f.result(); jobs += got; ok.add((a, s))
                for j in got:
                    j.slug = s
            except Exception as ex:
                errors.append(f"{a}/{s}: {ex}")
    print(f"  {len(ok)} feeds ok, {len(errors)} failed, {len(jobs)} postings")
    return jobs, ok, errors


def clean_search_title(title: str) -> tuple[str, str]:
    """'Senior Data Scientist - Acme GmbH' -> ('Senior Data Scientist', 'Acme GmbH')"""
    t = re.sub(r"\s*[|–-]\s*(Greenhouse|Lever|Ashby|Workable|Personio|Teamtailor|Workday|JOIN|Recruitee|SmartRecruiters).*$", "", title, flags=re.I)
    t = re.sub(r"^Job Application for\s+", "", t, flags=re.I)
    parts = re.split(r"\s+(?:at|@|[|–-])\s+", t, maxsplit=1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "")


def source_name(url: str) -> str:
    host = re.sub(r"^www\.", "", url.split("/")[2]) if "//" in url else url
    for dom, name in SOURCE_NAMES.items():
        if host.endswith(dom):
            return name
    return host


BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/124.0 Safari/537.36", "Accept-Language": "en,de;q=0.8"}


def _find_jobposting(obj):
    if isinstance(obj, list):
        for o in obj:
            if (r := _find_jobposting(o)):
                return r
    elif isinstance(obj, dict):
        t = obj.get("@type")
        if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
            return obj
        if "@graph" in obj:
            return _find_jobposting(obj["@graph"])
    return None


def read_jobposting(url: str) -> dict | None:
    """Read schema.org JobPosting data embedded in a public job page (used by XING, Teamtailor, Join...)."""
    r = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
    r.raise_for_status()
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', r.text, re.S | re.I):
        try:
            jp = _find_jobposting(json.loads(block.strip()))
        except Exception:
            continue
        if jp:
            return jp
    return None


def enrich_from_pages(jobs: list[Job], limit: int = 400) -> None:
    """Fill in real title/company/location/date for Google-only results from the job page itself."""
    todo = [j for j in jobs if not j.verified][:limit]
    if not todo:
        return
    print(f"Reading {len(todo)} job pages (XING / portals without a feed)")
    ok = 0

    def work(j: Job):
        jp = read_jobposting(j.url)
        if not jp:
            return False
        if jp.get("title"):
            j.title = re.sub(r"\s+", " ", jp["title"]).strip()
        org = jp.get("hiringOrganization")
        if isinstance(org, dict) and org.get("name"):
            j.company = org["name"]
        locs = jp.get("jobLocation") or []
        locs = locs if isinstance(locs, list) else [locs]
        parts = []
        for l in locs:
            a = (l or {}).get("address") or {}
            if isinstance(a, dict):
                parts.append(", ".join(filter(None, [a.get("addressLocality"), a.get("addressRegion"),
                                                      str(a.get("addressCountry") or "")
                                                      if not isinstance(a.get("addressCountry"), dict)
                                                      else a["addressCountry"].get("name", "")])))
        if any(parts):
            j.location = " / ".join(filter(None, parts))
        if jp.get("datePosted"):
            j.posted = parse_date(jp["datePosted"])
            j.verified = j.posted is not None
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(work, j) for j in todo]):
            try:
                ok += bool(f.result())
            except Exception:
                pass
    print(f"  structured data found on {ok} of {len(todo)} pages")


# LinkedIn public (logged-out) job search. Paced, and stops quietly if LinkedIn rate-limits.
LINKEDIN_LOCATIONS = {
    "Berlin": "Berlin, Germany", "Munich": "Munich, Bavaria, Germany",
    "Amsterdam": "Amsterdam, North Holland, Netherlands", "Brussels": "Brussels Region, Belgium",
    "Paris": "Paris, Île-de-France, France", "Copenhagen": "Copenhagen, Capital Region of Denmark, Denmark",
    "Warsaw": "Warsaw, Mazowieckie, Poland", "Austria": "Austria", "London": "London, England, United Kingdom",
    "Romania": "Romania", "Norway": "Norway", "Barcelona": "Barcelona, Catalonia, Spain",
}
LINKEDIN_PAGES = 4          # 10 jobs per page


def _li_field(pattern: str, s: str) -> str:
    m = re.search(pattern, s, re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1)))).strip() if m else ""


def fetch_linkedin(cities: list[str], hours: int) -> list[Job]:
    keywords = " OR ".join(f'"{t}"' if " " in t else t for t in SEARCH_TITLES)
    out = []
    print(f"Searching LinkedIn in {len(cities)} locations")
    for city in cities:
        n = 0
        for page in range(LINKEDIN_PAGES):
            time.sleep(random.uniform(1, 2))
            r = requests.get("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                             params={"keywords": keywords, "location": LINKEDIN_LOCATIONS[city],
                                     "f_TPR": f"r{hours * 3600}", "start": page * 10},
                             headers=BROWSER_HEADERS, timeout=TIMEOUT)
            if r.status_code == 429:
                print("  ! LinkedIn rate limit reached; skipping the remaining LinkedIn searches")
                return out
            if r.status_code != 200:
                break
            cards = re.findall(r"<li>(.*?)</li>", r.text, re.S)
            for c in cards:
                url = _li_field(r'href="(https://[^"]*linkedin\.com/jobs/view/[^"?]*)', c)
                if not url:
                    continue
                t = re.search(r'<time[^>]*datetime="([^"]*)"[^>]*>(.*?)</time>', c, re.S)
                posted = (parse_date(t.group(2).strip()) or parse_date(t.group(1))) if t else None   # "5 hours ago"
                # city stays empty: only jobs whose location really is one of the cities are kept
                out.append(Job(_li_field(r'base-search-card__title[^>]*>(.*?)</h3>', c),
                               _li_field(r'base-search-card__subtitle[^>]*>(.*?)</h4>', c),
                               _li_field(r'job-search-card__location[^>]*>(.*?)</span>', c),
                               url, "LinkedIn", posted))
                n += 1
            if len(cards) < 10:
                break
        print(f"  {city}: {n}")
    return out


def company_from_url(url: str) -> str:
    m = re.search(r"//([\w-]+)\.(?:teamtailor|wd\d+\.myworkdayjobs)\.com", url) \
        or re.search(r"join\.com/companies/([\w-]+)", url)
    return m.group(1).replace("-", " ").title() if m else ""

# ==========================================================================
# 3/4. FILTER, TAG, SCREEN
# ==========================================================================

def match_city(location: str) -> str:
    loc = (location or "").lower()
    for city, (_, keys) in CITIES.items():
        if any(k in loc for k in keys):
            return city
    return ""


def relevant(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in TITLE_PATTERNS) and not any(re.search(p, t) for p in EXCLUDE_PATTERNS)


def level_of(title: str) -> str:
    t = title.lower()
    return "Junior/Intern" if re.search(JUNIOR_RE, t) else "Senior+" if re.search(SENIOR_RE, t) else "Mid"


def filter_jobs(jobs, hours, cities, senior_only):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen, out = set(), []
    for j in jobs:
        if not j.title or not j.url or not relevant(j.title):
            continue
        j.city = match_city(j.location) or j.city
        if j.city not in cities:
            continue
        if j.verified and (j.posted is None or j.posted < cutoff):
            continue                                   # verified feeds: trust the real date
        if not j.verified and j.posted is not None and j.posted < cutoff:
            continue
        j.level = level_of(j.title)
        if senior_only and j.level != "Senior+":
            continue
        k = j.key()
        alt = (j.company.lower(), re.sub(r"\W+", " ", j.title.lower()).strip(), j.city)
        if k in seen or alt in seen:
            continue
        seen.update({k, alt}); out.append(j)
    return out


def llm_text(prompt: str, model: str) -> str:
    """Claude if ANTHROPIC_API_KEY is set; otherwise, or if Claude fails, the fallback model
    (FALLBACK_LLM_API_KEY / FALLBACK_LLM_MODEL, OpenAI by default)."""
    key, fallback_key = os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("FALLBACK_LLM_API_KEY")
    if key:
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=120,
                              headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                       "content-type": "application/json"},
                              json={"model": model, "max_tokens": 4000,
                                    "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])
        except Exception as ex:
            if not fallback_key:
                raise
            print(f"  ! Claude failed ({ex}); using the fallback model")
    base = os.environ.get("FALLBACK_LLM_BASE_URL", "https://api.openai.com/v1")
    r = requests.post(base.rstrip("/") + "/chat/completions", timeout=float(os.environ.get("FALLBACK_LLM_TIMEOUT_SECONDS", 300)),
                      headers={"Authorization": f"Bearer {fallback_key}"},
                      json={"model": os.environ.get("FALLBACK_LLM_MODEL", ""),
                            "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return re.sub(r"<think>.*?</think>", "", r.json()["choices"][0]["message"]["content"] or "", flags=re.S)


def claude_screen(jobs: list[Job], model: str) -> list[Job]:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("FALLBACK_LLM_API_KEY")):
        print("  ! ANTHROPIC_API_KEY / FALLBACK_LLM_API_KEY not set; skipping screening")
        return jobs
    kept = []
    for i in range(0, len(jobs), 40):
        batch = jobs[i:i + 40]
        listing = "\n".join(f"{n}. {j.title} | {j.company} | {j.location}" for n, j in enumerate(batch))
        prompt = ("You screen job postings for someone seeking AI engineering, data science, machine "
                  "learning engineering, forward-deployed engineering and AI consultant roles. For each numbered job "
                  "return {\"i\": number, \"relevant\": true/false (false for sales, recruiting, "
                  "non-technical, tutoring or data-annotation gigs), \"level\": \"Junior/Intern\"|\"Mid\"|"
                  "\"Senior+\", \"note\": max 8 words on the role focus}. Respond with ONLY a JSON array.\n\n"
                  + listing)
        try:
            text = llm_text(prompt, model)
            verdicts = {v["i"]: v for v in json.loads(text[text.find("["):text.rfind("]") + 1])}
        except Exception as ex:
            print(f"  ! Screening batch failed ({ex}); keeping it unscreened")
            kept += batch; continue
        for n, j in enumerate(batch):
            v = verdicts.get(n, {})
            if v.get("relevant", True):
                j.level, j.note = v.get("level", j.level), v.get("note", "")
                kept.append(j)
    print(f"  Screening kept {len(kept)} of {len(jobs)}")
    return kept

# ==========================================================================
# 4b. DETAILS - full job description of every match, one Markdown file per job
# ==========================================================================

def html_to_text(s: str | None) -> str:
    s = html.unescape(s or "")                      # Greenhouse sends escaped HTML
    s = re.sub(r"(?i)<h\d[^>]*>", "\n\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "\n- ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|ul|ol|li)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", s).strip()


@lru_cache(maxsize=None)
def _ashby_board(slug: str) -> dict:
    return {j["id"]: j for j in get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", [])}


@lru_cache(maxsize=None)
def _personio_board(host: str) -> dict:
    r = requests.get(f"https://{host}/xml", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return {p.findtext("id"): p for p in ET.fromstring(r.content).iter("position")}


def fetch_description(j: Job) -> str:
    """The job's full description as plain text, from the portal's API (or the page's schema.org data)."""
    last = j.key().split("/")[-1]
    if j.slug and j.source == "Greenhouse":
        jid = re.search(r"gh_jid=(\d+)|/jobs/(\d+)", j.url)
        d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{j.slug}/jobs/{jid.group(1) or jid.group(2)}")
        return html_to_text(d.get("content"))
    if j.slug and j.source == "Lever":
        for host in ("api.lever.co", "api.eu.lever.co"):
            try:
                d = get_json(f"https://{host}/v0/postings/{j.slug}/{last}")
            except requests.HTTPError:
                continue
            parts = [d.get("descriptionPlain", "")]
            parts += [f"{x.get('text', '')}\n{html_to_text(x.get('content'))}" for x in d.get("lists") or []]
            return "\n\n".join(filter(None, parts + [d.get("additionalPlain", "")])).strip()
    if j.slug and j.source == "Ashby":
        d = _ashby_board(j.slug).get(last) or {}
        return d.get("descriptionPlain") or html_to_text(d.get("descriptionHtml"))
    if j.slug and j.source == "SmartRecruiters":
        secs = get_json(f"https://api.smartrecruiters.com/v1/companies/{j.slug}/postings/{last}")["jobAd"]["sections"]
        return "\n\n".join(f"{s.get('title', '')}\n{html_to_text(s.get('text'))}".strip()
                           for s in secs.values() if isinstance(s, dict) and s.get("text"))
    if j.slug and j.source == "Recruitee":
        d = get_json(f"https://{j.slug}.recruitee.com/api/offers/{last}")["offer"]
        return "\n\n".join(filter(None, [html_to_text(d.get("description")), html_to_text(d.get("requirements"))]))
    if j.slug and j.source == "Workable":
        d = get_json(f"https://apply.workable.com/api/v2/accounts/{j.slug}/jobs/{last}")
        return "\n\n".join(filter(None, (html_to_text(d.get(k)) for k in ("description", "requirements", "benefits"))))
    if j.slug and j.source == "Personio":
        p = _personio_board(j.url.split("/")[2]).get(last)
        if p is not None:
            return "\n\n".join(f"{d.findtext('name') or ''}\n{html_to_text(d.findtext('value'))}".strip()
                               for d in p.findall("jobDescriptions/jobDescription"))
    if j.source == "LinkedIn":
        time.sleep(random.uniform(1.5, 3))
        r = requests.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{re.search(r'(\d+)$', j.key()).group(1)}",
                         headers=BROWSER_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', r.text, re.S)
        return html_to_text(m.group(1)) if m else ""
    jp = read_jobposting(j.url)                     # XING, Teamtailor, Join, Workday, Google-only results
    return html_to_text(jp.get("description")) if jp else ""


def jd_filename(j: Job) -> str:
    name = re.sub(r"[^\w]+", "_", f"{j.company}_{j.title}").strip("_")[:80]
    return f"{name}_{hashlib.md5(j.key().encode()).hexdigest()[:6]}.md"


def write_details(jobs: list[Job], out_dir: Path) -> None:
    """Write out_dir/jd/<Company>_<Title>_<id>.md for each job: position, place, opening date, link, full JD.
    Usable directly as `resume_tailor.py --jd <file>`."""
    jd_dir = Path(out_dir) / "jd"
    jd_dir.mkdir(parents=True, exist_ok=True)
    todo = [j for j in jobs if not (jd_dir / jd_filename(j)).exists()]
    if not todo:
        return
    print(f"Fetching {len(todo)} job descriptions")

    def work(j: Job):
        try:
            text = fetch_description(j)
        except requests.HTTPError as ex:
            if ex.response is not None and ex.response.status_code == 429:
                raise                                   # rate-limited: write nothing, retry on the next run
            text = f"_Could not fetch the description ({ex}); open the link above._"
        except Exception as ex:
            text = f"_Could not fetch the description ({ex}); open the link above._"
        opened = f"{j.posted.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC ({age(j.posted)})" if j.posted else "unknown"
        (jd_dir / jd_filename(j)).write_text(
            f"# {j.title}\n\n"
            f"- **Company:** {j.company}\n- **Location:** {j.location or j.city}\n- **Opened:** {opened}\n"
            f"- **Level:** {j.level}\n- **Apply:** {j.url} ({j.source})\n\n"
            f"## Job description\n\n{text or '_No description published; open the link above._'}\n",
            encoding="utf-8")

    linkedin = [j for j in todo if j.source == "LinkedIn"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, [j for j in todo if j.source != "LinkedIn"]))
    for i, j in enumerate(linkedin):                    # LinkedIn only tolerates slow, one-at-a-time reads
        for attempt in range(2):
            try:
                work(j)
                break
            except requests.HTTPError:
                if attempt == 0:
                    time.sleep(60)
        else:
            print(f"  ! LinkedIn rate limit: {len(linkedin) - i} descriptions left for the next run")
            break

# ==========================================================================
# 4b. VISA SPONSORSHIP / RELOCATION
# ==========================================================================

# Phrases in a JD (English + German). Negative phrases are checked first: "we cannot offer visa
# sponsorship" also contains "visa sponsorship".
# "<thing> (support) is not available / will not be provided ..."
_NOT_OFFERED = r"{}\s+(\w+\s+){{0,2}}(is\s+|are\s+|will\s+)?not\s+(be\s+)?(available|offered|provided|possible|supported|covered)"
VISA_NO_RE = re.compile(
    r"(no|not|cannot|can't|can ?not|unable to|do not|don't|won't|will not|are not able to)\s+(\w+\s+){0,4}"
    r"(visa\s+)?sponsor|without\s+(the\s+need\s+for\s+)?(visa\s+)?sponsorship|"
    r"(must|should)\s+(already\s+)?(have|hold|possess)\s+(the\s+|a\s+|an\s+)?(valid\s+)?"
    r"(right|eligibility|authori[sz]ation|work permit|permission)\s+to\s+work|"
    r"must\s+(already\s+)?be\s+(legally\s+)?(eligible|authori[sz]ed|entitled|permitted)\s+to\s+work|"
    r"keine\s+(visa|visum)|kein(e)?\s+sponsoring|" + _NOT_OFFERED.format(r"(visa\s+)?sponsorship"), re.I)
VISA_YES_RE = re.compile(
    r"visa\s+sponsor|sponsor(ship|ing)?\s+(of\s+)?(your\s+|a\s+|the\s+)?(work\s+)?(visa|permit)|"
    r"(visa|work permit|blue card)\s+(support|assistance|process|application|help)|"
    r"(support|help|assist)\w*\s+(you\s+)?with\s+(your\s+|the\s+)?(visa|work permit|blue card)|"
    r"visum(s)?unterstützung|unterstützung\s+(beim|bei der)\s+visum", re.I)
RELOC_NO_RE = re.compile(r"(no|not|cannot|unable to|do not|don't|without)\s+(\w+\s+){0,3}relocation|"
                         r"keine\s+umzugs|" + _NOT_OFFERED.format("relocation"), re.I)
RELOC_YES_RE = re.compile(
    r"relocation\s+(support|package|assistance|bonus|allowance|budget|help|costs?|benefits?|"
    r"is\s+(provided|offered|available|possible|supported)|(will\s+be\s+)?covered)|"
    r"(support|help|assist)\w*\s+(you\s+)?(with\s+)?(your\s+)?relocat|relocate\s+you|"
    r"umzugs(unterstützung|kosten|pauschale|hilfe)|relocation\s+&\s+visa|visa\s+&\s+relocation|"
    r"expat(riate)?\s+(package|support|program(me)?|allowance|benefits?|services?|assistance|community)|"
    r"(support|help|assist)\w*\s+(for\s+)?expat|30\s*%\s*(tax\s+)?(ruling|regeling|facility)", re.I)

VISA_CACHE_DAYS = 30


def _visa_from_text(text: str) -> tuple[str, str]:
    """(visa, relocation) stated in `text`: "yes", "no" or ""."""
    visa = "no" if VISA_NO_RE.search(text) else "yes" if VISA_YES_RE.search(text) else ""
    reloc = "no" if RELOC_NO_RE.search(text) else "yes" if RELOC_YES_RE.search(text) else ""
    return visa, reloc


def _web_snippets(query: str) -> list[dict]:
    """Search results with snippets: Serper if configured, else free Bing (paced)."""
    if key := os.environ.get("SERPER_API_KEY"):
        r = requests.post("https://google.serper.dev/search", timeout=TIMEOUT,
                          headers={"X-API-KEY": key, "Content-Type": "application/json"}, json={"q": query, "num": 10})
        r.raise_for_status()
        return [{"url": o.get("link", ""), "text": f"{o.get('title', '')} {o.get('snippet', '')}"}
                for o in r.json().get("organic", [])]
    from ddgs import DDGS
    time.sleep(float(os.environ.get("VISA_SEARCH_DELAY", 10)) * random.uniform(1, 1.5))
    res = DDGS().text(query, max_results=10, backend="bing")
    return [{"url": r.get("href", ""), "text": f"{r.get('title', '')} {r.get('body', '')}"} for r in res]


# Job city -> country, for country-specific web evidence (sponsorship rules differ per country).
CITY_COUNTRY = {"Berlin": "Germany", "Munich": "Germany", "Amsterdam": "Netherlands", "Brussels": "Belgium",
                "Paris": "France", "Copenhagen": "Denmark", "Warsaw": "Poland", "Austria": "Austria",
                "London": "UK", "Romania": "Romania", "Norway": "Norway",
                "Barcelona": "Spain"}
# US-only evidence (H-1B data, US career pages) says nothing about a European job.
US_ONLY_RE = re.compile(r"\bh-?1b\b|\busa\b|united states|\bu\.s\.|/en[_-]us/", re.I)
US_ONLY_SITES = ("myvisajobs.com", "h1bdata.info", "h1bgrader.com", "h1bsponsors", "usponsor")


def _company_visa_web(company: str, country: str = "") -> dict:
    """Ask the web whether `company` sponsors visas / helps relocate in `country`.

    Evidence must name the company, and US-only pages are ignored for non-US jobs. The company's own
    site is preferred over aggregators.
    """
    name = re.sub(r"\b(gmbh|ag|se|ltd|limited|inc|plc|bv|b\.v\.|sas|sa|s\.a\.|ab|as|oy|llc)\b\.?", "", company, flags=re.I)
    tokens = [t for t in re.findall(r"\w+", name.lower()) if len(t) > 2] or [company.lower()]
    out = {"visa": "", "relocation": "", "src": "", "official": False, "checked": datetime.now(timezone.utc).isoformat()}
    domain = lambda u: u.split("/")[2].lower() if u.count("/") >= 2 else ""
    results = sorted(_web_snippets(f'"{name.strip()}" visa sponsorship relocation expat {country}'.strip()),
                     key=lambda r: tokens[0] not in domain(r["url"]))
    for r in results:
        text, url = r["text"], r["url"]
        if not all(t in f"{text} {url}".lower() for t in tokens[:2]):
            continue                                    # about another company
        if country != "USA" and (any(site in url for site in US_ONLY_SITES) or US_ONLY_RE.search(f"{text} {url}")):
            continue                                    # US sponsorship, not this country's
        visa, reloc = _visa_from_text(text)
        if (visa and not out["visa"]) or (reloc and not out["relocation"]):
            if not out["src"]:
                out["src"], out["official"] = url, tokens[0] in domain(url)
            out["visa"] = out["visa"] or visa
            out["relocation"] = out["relocation"] or reloc
        if out["visa"] and out["relocation"]:
            break
    return out


def check_visa_relocation(jobs: list[Job], out_dir: Path, web_limit: int | None = None) -> None:
    """Mark each job's visa sponsorship and relocation support.

    1. The job description (reliable, free): explicit "visa sponsorship" / "relocation package" / "no
       sponsorship" / "must have the right to work" phrases.
    2. Where the JD is silent: one web search per company and country, cached for VISA_CACHE_DAYS in
       out_dir/visa_companies.json. At most `web_limit` new searches per run (free Bing is slow);
       the rest are checked on later runs. Web answers are company-level hints, shown as "likely".
    """
    jd_dir = Path(out_dir) / "jd"
    for j in jobs:
        f = jd_dir / jd_filename(j)
        if f.exists():
            j.visa, j.relocation = _visa_from_text(f.read_text(encoding="utf-8").split("## Job description", 1)[-1])
            j.visa_src = "JD" if j.visa else ""
            j.reloc_src = "JD" if j.relocation else ""

    cache_file = Path(out_dir) / "visa_companies.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    ckey = lambda j: f"{j.company}|{CITY_COUNTRY.get(j.city, '')}"
    fresh = lambda k: k in cache and datetime.now(timezone.utc) - datetime.fromisoformat(cache[k]["checked"]) < timedelta(days=VISA_CACHE_DAYS)
    unknown = [j for j in jobs if (not j.visa or not j.relocation) and j.company]
    # Company-site jobs first (fewer, direct), then by how many open jobs the company has there.
    counts: dict[str, int] = {}
    for j in unknown:
        counts[ckey(j)] = counts.get(ckey(j), 0) + 1
    todo = sorted({ckey(j) for j in unknown if not fresh(ckey(j))},
                  key=lambda k: (all(is_linkedin(j) for j in unknown if ckey(j) == k), -counts[k]))
    limit = int(os.environ.get("VISA_WEB_LIMIT", 25)) if web_limit is None else web_limit
    if todo and limit:
        print(f"Checking visa sponsorship / relocation on the web for {min(len(todo), limit)} of {len(todo)} companies")
    for k in todo[:limit]:
        company, country = k.split("|", 1)
        try:
            cache[k] = _company_visa_web(company, country)
        except Exception as ex:
            print(f"  ✗ {company}: {ex}")
            continue
        cache_file.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    for j in unknown:
        c = cache.get(ckey(j))
        if not c or not c["src"]:
            continue
        src = c["src"] if c.get("official") else f"3rd:{c['src']}"
        if not j.visa and c["visa"]:
            j.visa, j.visa_src = c["visa"], src
        if not j.relocation and c["relocation"]:
            j.relocation, j.reloc_src = c["relocation"], src


def _mark(value: str, src: str) -> str:
    """✅ / ❌ when the JD says so; 'likely' / 'unlikely' + link when it is the company's answer online."""
    if not value:
        return "❔"
    if src == "JD":
        return ("✅" if value == "yes" else "❌") + " (JD)"
    site = f"[other site]({src[4:]})" if src.startswith("3rd:") else f"[company site]({src})"
    return f"{'likely' if value == 'yes' else 'unlikely'} ({site})"


def visa_cell(j: Job) -> str:
    """Compact table cell, e.g. 'Visa ✅ (JD) · Reloc likely ([company site](...))'."""
    if not (j.visa or j.relocation):
        return "❔"
    return f"Visa {_mark(j.visa, j.visa_src)} · Reloc {_mark(j.relocation, j.reloc_src)}"


# ==========================================================================
# 5. WRITE MARKDOWN
# ==========================================================================

def esc(s): return (s or "").replace("|", "/").replace("\n", " ").strip()


def age(dt):
    if not dt:
        return "new (date n/a)"
    h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    return f"{max(h, 0):.0f}h ago" if h < 48 else f"{h / 24:.0f}d ago"


def is_linkedin(j) -> bool:
    return j.source == "LinkedIn"


def write_markdown(jobs, path, hours, cities, new_keys, stats):
    """One file, two parts: jobs from company career sites / job boards first, then LinkedIn."""
    now = datetime.now(timezone.utc)
    direct = [j for j in jobs if not is_linkedin(j)]
    linkedin = [j for j in jobs if is_linkedin(j)]
    L = [f"# AI / ML / Data Science jobs - last {hours}h", "",
         f"Generated {now:%Y-%m-%d %H:%M} UTC · {len(jobs)} jobs ({len(direct)} company sites, "
         f"{len(linkedin)} LinkedIn) · {len(new_keys)} new since last run (🆕) · "
         f"{stats['companies']} companies checked", "",
         "| City | Company sites | LinkedIn |", "|---|---|---|"]
    L += [f"| {c} | {sum(j.city == c for j in direct)} | {sum(j.city == c for j in linkedin)} |" for c in cities] + [""]
    by_src: dict[str, int] = {}
    for j in jobs:
        by_src[j.source] = by_src.get(j.source, 0) + 1
    if by_src:
        L += ["| Source | Jobs |", "|---|---|"]
        L += [f"| {s} | {n} |" for s, n in sorted(by_src.items(), key=lambda x: -x[1])] + [""]
    visa_yes = sum(j.visa == "yes" and j.visa_src == "JD" for j in jobs)
    reloc_yes = sum(j.relocation == "yes" and j.reloc_src == "JD" for j in jobs)
    visa_likely = sum(j.visa == "yes" and j.visa_src != "JD" for j in jobs)
    L += [f"**Visa sponsorship:** {visa_yes} jobs say yes, {visa_likely} more likely · "
          f"**Relocation support:** {reloc_yes} jobs say yes. Marks: "
          "stated in the job description (✅ yes / ❌ no). Where the JD is silent, the company's answer "
          "online for that country is shown as likely / unlikely: [company site] = its own website, "
          "[other site] = a third-party page (weakest, check it). ❔ = nothing found.", ""]
    L += ["**Jump to:** [Company career sites](#part-1-company-career-sites) · [LinkedIn](#part-2-linkedin)", ""]
    L += _job_part("# Part 1: Company career sites", direct, path, cities, new_keys, now)
    L += _job_part("# Part 2: LinkedIn", linkedin, path, cities, new_keys, now)
    L += ["---", "",
          "Jobs marked **(unverified)** had no readable posting date or location on the page "
          "(often Workday, or XING pages that blocked the request), so those details come from Google - "
          "double-check them."]
    path.write_text("\n".join(L), encoding="utf-8")


def _job_part(heading, jobs, path, cities, new_keys, now) -> list[str]:
    """One part of the report: its jobs grouped by city (cities without jobs are skipped)."""
    L = [heading, "", f"{len(jobs)} jobs", ""]
    if not jobs:
        return L + ["_No matching jobs in this window._", ""]
    notes = any(j.note for j in jobs)
    for city in cities:
        items = sorted((j for j in jobs if j.city == city), key=lambda j: (j.posted or now), reverse=True)
        if not items:
            continue
        L += [f"## {city} ({len(items)})", ""]
        head = "| | Title | Company | Level | Location | Opened | Visa / Relocation | JD | Source |" + (" Focus |" if notes else "")
        L += [head, "|" + "---|" * (head.count("|") - 1)]
        for j in items:
            src = j.source if j.verified else f"{j.source} (unverified)"
            opened = f"{j.posted.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC ({age(j.posted)})" if j.posted else age(j.posted)
            jd = next((Path(os.path.relpath(d / "jd" / jd_filename(j), path.parent)).as_posix()
                       for d in (path.parent, path.parent.parent) if (d / "jd" / jd_filename(j)).exists()), "")
            row = (f"| {'🆕' if j.key() in new_keys else ''} | [{esc(j.title)}]({j.url}) | {esc(j.company)} | "
                   f"{j.level} | {esc(j.location)[:60]} | {opened} | {visa_cell(j)} | {f'[JD]({jd})' if jd else '-'} | {src} |")
            L.append(row + (f" {esc(j.note)} |" if notes else ""))
        L.append("")
    return L


# ==========================================================================
# Main
# ==========================================================================

def load_known(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text()) or {}
    return {(a, (e["slug"] if isinstance(e, dict) else e)) for a, lst in data.items() if a in FETCHERS for e in (lst or [])}


def save_known(path: Path, companies: set[tuple[str, str]]):
    out: dict[str, list[str]] = {}
    for a, s in sorted(companies):
        out.setdefault(a, []).append(s)
    path.write_text("# Auto-generated: every company the script has found. Checked directly on each run.\n"
                    + yaml.safe_dump(out, sort_keys=True))


def run(hours: int = 24, cities: list[str] | None = None, senior_only: bool = False, out_dir: str = "jobs",
        extra_companies: str = "companies.yaml", xing_all_cities: bool = False, no_memory: bool = False,
        claude: bool = False, model: str = "claude-sonnet-5", write_files: bool = True,
        linkedin: bool = False, visa_check: bool = True) -> dict:
    """Run the whole search and write the Markdown files (unless write_files=False).
    Returns the paths and matching jobs."""
    cities = list(CITIES) if cities is None else cities
    if bad := [c for c in cities if c not in CITIES]:
        raise ValueError(f"Unknown city {bad}; choose from {list(CITIES)}")

    out_dir = Path(out_dir); out_dir.mkdir(exist_ok=True)
    memory = out_dir / "discovered_companies.yaml"

    # 1. discover
    hits = discover(cities, hours, senior_only, xing_all_cities)

    # 2. verify: feeds for discovered + remembered + extra companies
    found = {x for _, r in hits if (x := identify(r["url"]))}
    known = set() if no_memory else load_known(memory)
    extra = load_known(Path(extra_companies))
    feed_jobs, ok, errors = fetch_feeds(found | known | extra)
    print(f"  new companies this run: {len(found - known)}")

    # Google-only results (no feed, or feed failed)
    feed_urls = {j.key() for j in feed_jobs}
    google_jobs = []
    for city, r in hits:
        ident = identify(r["url"])
        if ident and ident in ok:
            continue
        title, comp = clean_search_title(r["title"])
        job = Job(title, comp or company_from_url(r["url"]) or (ident[1] if ident else ""), city,
                  r["url"], (ident[0].title() if ident else source_name(r["url"])),
                  parse_date(r.get("date")), city=city, verified=False)
        if job.key() not in feed_urls:
            google_jobs.append(job)

    enrich_from_pages(google_jobs)
    linkedin_jobs = fetch_linkedin(cities, hours) if linkedin else []

    # 3/4. filter + screen
    jobs = filter_jobs(feed_jobs + google_jobs + linkedin_jobs, hours, cities, senior_only)
    print(f"{len(feed_jobs) + len(google_jobs) + len(linkedin_jobs)} postings -> {len(jobs)} matching")
    if claude:
        jobs = claude_screen(jobs, model)

    # remember companies & seen jobs
    save_known(memory, known | ok)
    seen_file = out_dir / "seen.json"
    seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
    new_keys = {j.key() for j in jobs} - seen
    seen_file.write_text(json.dumps(sorted(seen | new_keys)))

    result = {"jobs": jobs, "new_keys": new_keys, "companies_checked": len(ok), "feed_errors": len(errors)}
    if not write_files:
        return result

    # 5. write
    write_details(jobs, out_dir)
    if visa_check:
        check_visa_relocation(jobs, out_dir)
    path = out_dir / f"jobs_{datetime.now():%Y-%m-%d_%H%M}.md"
    write_markdown(jobs, path, hours, cities, new_keys, {"companies": len(ok)})
    latest = out_dir / "latest.md"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Saved {path} and {latest}")
    return {**result, "path": path, "latest": latest}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--cities", nargs="*", default=list(CITIES), help="subset of: " + ", ".join(CITIES))
    ap.add_argument("--senior-only", action="store_true")
    ap.add_argument("--out-dir", default="jobs")
    ap.add_argument("--extra-companies", default="companies.yaml",
                    help="optional YAML of companies to always check (not required)")
    ap.add_argument("--xing-all-cities", action="store_true",
                    help="search XING for every city, not only Berlin/Munich/Austria")
    ap.add_argument("--no-memory", action="store_true", help="don't re-check previously discovered companies")
    ap.add_argument("--claude", action="store_true", help="screen with Claude (ANTHROPIC_API_KEY) or the fallback model (FALLBACK_LLM_*)")
    ap.add_argument("--linkedin", action="store_true", help="also search LinkedIn's public job search")
    ap.add_argument("--no-visa-check", action="store_true",
                    help="skip marking visa sponsorship / relocation support (JD scan + web search)")
    ap.add_argument("--model", default=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"))
    a = ap.parse_args()
    try:
        run(a.hours, a.cities, a.senior_only, a.out_dir, a.extra_companies, a.xing_all_cities,
            a.no_memory, a.claude, a.model, linkedin=a.linkedin, visa_check=not a.no_visa_check)
    except (ValueError, RuntimeError) as ex:
        sys.exit(str(ex))


if __name__ == "__main__":
    main()
