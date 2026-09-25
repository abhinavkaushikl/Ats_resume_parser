# Step 1 - Find today's jobs

**Cities:** Berlin, Munich, Amsterdam, Brussels, Paris, Copenhagen, Warsaw, Austria (Vienna, Graz, Linz),
London, Romania (Bucharest, Cluj), Norway (Oslo, Bergen).

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

## b. Run the job search (background, about 10 minutes plus scoring)

```
.venv/bin/python daily_jobs.py
```

It downloads every known company's job feed and LinkedIn's public job search, keeps matching roles in
these cities posted in the last 24 hours, and writes:

- `jobs/jobs_<today>_<HHMM>.md` - every job, one table per city, with a `[JD](jd/...)` link per row.
  **This is the input for step 2.**
- `jobs/daily/jobs_<today>.md` - the same jobs with each JD scored against the resume; jobs below 60% are
  listed in its "Skipped - resume match below 60%" section.

## c. Check

- Both files exist and the job count is plausible (a normal day is 100-300 jobs).
- Note the jobs in the "Skipped - resume match below 60%" section of the daily file: step 2 does not need
  to visa-check those.

Status line: "Step 1 done - N jobs found (M skipped below 60%), K new companies added."
