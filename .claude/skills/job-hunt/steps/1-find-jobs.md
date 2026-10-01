# Step 1 - Find the last 24 hours' jobs (one file)

**Cities:** Berlin, Munich, Germany (every other German city: Hamburg, Frankfurt, Cologne, Stuttgart,
Düsseldorf, Leipzig ...), Amsterdam, Brussels, Paris, Copenhagen, Warsaw, Austria (Vienna, Graz, Linz),
London, Romania (Bucharest, Cluj), Norway (Oslo, Bergen), Barcelona (Spain), Switzerland (Zurich, Geneva,
Basel, Lausanne), Sweden (Stockholm, Gothenburg, Malmö), Italy (Milan, Rome, Turin, Bologna).

**Roles:** data scientist, ML engineer, AI engineer, applied scientist, research scientist, MLOps, GenAI,
LLM, NLP, computer vision, deep learning, AI developer, AI specialist, AI consultant, forward deployed
engineer.

## a. Discover new companies (web search, about 25 searches)

Search each career portal per city (batch cities where it helps), e.g.

```
site:job-boards.greenhouse.io Berlin "machine learning" OR "AI engineer" OR "data scientist"
```

Portals: job-boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com, jobs.smartrecruiters.com,
apply.workable.com, jobs.personio.de, recruitee.com.

From each career-portal link, take the company's board name (the part after the portal domain, or the
subdomain for Personio / Recruitee) and add it under the right portal in `companies.yaml`. Skip names
already in `companies.yaml` or `jobs/discovered_companies.yaml`, and skip job aggregators.

## b. Run the job search (background, about 10 minutes)

Check first that no other copy is running: `pgrep -fl daily_jobs`. Then:

```
.venv/bin/python daily_jobs.py --hours 24
```

(add `--cities Berlin Amsterdam` etc. if I named cities when starting the run).

It reads every known company's job feed plus LinkedIn's public job search, keeps matching roles in these
cities posted in the last 24 hours, and writes **one file and nothing else**:

`jobs/jobs_<today>.md` - Part 1 company career sites, Part 2 LinkedIn, one `## <City> (n)` table per city:

```
| Visa | Company | Job | City | Opened | Link |
```

The `Visa` column is empty - step 2 fills it in this same file. No job descriptions are downloaded and
nothing is scored; the `Link` cell is the posting URL, which is all I need to read the job myself.

## c. Check

- `jobs/jobs_<today>.md` exists and the job count is plausible (a normal day is 100-300 jobs).
- No `jobs/jd/`, `jobs/daily/` or `jobs/latest.md` was created by this run (the script no longer writes
  them). If an old one is lying around from a previous version, leave it - don't build on it.

Status line: "Step 1 done - N jobs in jobs/jobs_<today>.md (D company sites, L LinkedIn), K new companies added."
