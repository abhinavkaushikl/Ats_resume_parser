# Morning job prompt

Open Claude Code in this folder (`/Users/abhinav/Ats_resume_parser`) and paste everything inside the box below.

```text
Fetch today's AI / ML jobs. Last 24 hours only - never widen the window.

Cities: Berlin, Munich, Amsterdam, Brussels, Paris, Copenhagen, Warsaw, Austria (Vienna, Graz, Linz),
London, Romania (Bucharest, Cluj), Norway (Oslo, Bergen).
Roles: data scientist, machine learning / ML engineer, AI engineer, applied scientist, research scientist,
MLOps, GenAI / generative AI, LLM, NLP, computer vision, deep learning, AI developer, AI specialist,
AI consultant, forward deployed engineer.
Portals: Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Personio, Recruitee.

Steps:
1. Discover companies with web search. For every city, search each portal for the roles above, e.g.
   site:job-boards.greenhouse.io Berlin "machine learning" OR "AI engineer" OR "data scientist"
   (portals: job-boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com, jobs.smartrecruiters.com,
   apply.workable.com, jobs.personio.de, recruitee.com). Batch cities where it helps; about 25 searches is enough.
2. From each career-portal link, take the company's board name (the part after the portal domain, or the
   subdomain for Personio / Recruitee) and add it under the right portal in companies.yaml.
   Skip names already in companies.yaml or jobs/discovered_companies.yaml, and skip job aggregators.
3. Run: .venv/bin/python daily_jobs.py   (takes about 10 minutes - run it in the background)
   It downloads every known company's official job feed and searches LinkedIn for every city, keeps only
   matching roles in these cities posted in the last 24 hours, and writes one file: jobs/daily/jobs_<today>.md
   (title, company, location, posting time, link, full job description).
4. Reply with the file path, the number of jobs per city, and the 5 jobs that best fit my resume
   (Abhinav_kaushik_AI_ML.pdf - Senior AI / GenAI / LLM engineer). Don't paste the job descriptions.
```

## Without Claude

`.venv/bin/python daily_jobs.py` alone gives the same file, but only checks the companies already known.
With a `SERPER_API_KEY` in `.env` it also discovers new companies on its own, so it can run from cron.
