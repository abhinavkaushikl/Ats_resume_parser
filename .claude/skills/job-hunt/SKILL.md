---
name: job-hunt
description: Daily AI/ML job hunt for Abhinav, end to end - find jobs posted in the last 24 hours, keep only companies that sponsor visas (with a Google check and deeper research), get the full job descriptions (company site first, else LinkedIn public page), score the visa-confirmed ones against the base resume, write one results file with analysis, and generate a subtly tailored resume + cover letter for every visa-confirmed job at 50%+ (visa-unsure jobs are only listed for review). Use when the user asks to run the job hunt, fetch today's jobs, or runs /job-hunt.
---

# Daily job hunt

Run the whole job hunt in this project folder (`/Users/abhinav/Ats_resume_parser`) without asking me
questions along the way. If I added notes when starting (e.g. "only Berlin and Amsterdam"), apply them.

Base resume: `Abhinav_kaushik_AI_ML.pdf` (Senior AI / GenAI / LLM engineer).
The end result is ONE file: `JOB_RESULTS.md` in the project root, plus the job-description files of the
shortlisted jobs and a tailored resume + cover letter for each (`applications/<date>/`).
- **Visa confirmed** (`Visa: yes`): JD fetched and scored; **50%+ match -> resume + cover letter**, below
  50% -> no resume (still listed).
- **Visa unsure** (⚠️ weak evidence or unclear): **no JD, no score, no resume** - listed in JOB_RESULTS.md
  under "Visa unsure - waiting for your review". I review them myself and name the ones to process
  (step 3 e), then those get the same treatment.
- Dropped: company says no, existing right to work required, or a recruitment agency hiding the employer.
Everything else is working data and is cleaned up at the end.

## How to run

Do the steps in order. Before each step, read its file in `steps/` and follow it exactly. After each step,
give me one status line (e.g. "Step 2 done - 88 of 261 jobs kept after visa check").

1. [steps/1-find-jobs.md](steps/1-find-jobs.md) - find today's jobs, first resume filter
2. [steps/2-visa-check.md](steps/2-visa-check.md) - visa sponsorship check + deeper research with Google
3. [steps/3-job-descriptions.md](steps/3-job-descriptions.md) - full JDs (company site, else LinkedIn), scored
4. [steps/4-results.md](steps/4-results.md) - JOB_RESULTS.md + written analysis
5. [steps/5-tailor-resumes.md](steps/5-tailor-resumes.md) - tailored resume + cover letter for every shortlisted job
6. [steps/6-cleanup-and-reply.md](steps/6-cleanup-and-reply.md) - delete working files, reply to me

Long scripts (job search, extraction) run in the background; wait for them to finish before the next step.

## Ground rules (whole run)

- **Last 24 hours only.** Never widen the time window.
- **LinkedIn separate.** Keep LinkedIn jobs in their own section in every list and in the results.
- **Job descriptions: company site first, then LinkedIn.** Try the company's own site or ATS (Playwright)
  first. If it isn't there, read LinkedIn's public job page - never log in, never use my account, go slowly,
  and stop using LinkedIn for the rest of the run if it rate-limits (the extractor does this by itself).
- **Honest scores.** Never make the scorer more lenient, never pick a higher re-score, never tell the scorer
  what score to aim for. A job that needs experience I don't have should score low - report it as it is.
- **Visa: keep any hope.** Keep a company with even slight public evidence of sponsorship (flag weak
  evidence); drop only explicit "no", "must already have work rights", or agencies hiding the employer.
- **Don't destroy work mid-run.** Never delete `jobs/jd_visa/<today>/` while the run is going; re-run steps
  on top of what is there (scores are cached in `outputs/.cache/`). Only one run of each script at a time -
  check with `pgrep -fl <script>` before starting one. If another session is running the same scripts,
  stop and tell me instead of starting a second copy.
- **One results file.** Don't create other report files for me; everything I need goes in JOB_RESULTS.md.
- If a step fails, say what failed and why, continue with what you have, and list it in the final reply.

## Scripts (all in the project root, run with `.venv/bin/python`)

| Script | Does |
|---|---|
| `daily_jobs.py` | Last-24h jobs from company feeds + LinkedIn; writes `jobs/jobs_<date>_<HHMM>.md` (table + JD links to `jobs/jd/`) and `jobs/daily/jobs_<date>.md` (scored, below-60% listed as skipped) |
| `sponsor_registers.py <list.md>` | Step 2 first: matches companies against the UK / NL / DK sponsor registers and the DE / ES employer lists (auto-downloaded weekly to `jobs/registers/`), caches hits in `jobs/visa_companies.json` |
| `jd_extractor.py <list.md>` | Full JDs: company site (Playwright), else LinkedIn's public page (no login); each scored on save: 60%+ -> `jobs/jd_visa/<date>/`, below -> `skipped/` |
| `job_match.py <folder>` | Re-scores every JD file in a folder (cached) |
| `unclear_visa_match.py <visa.md>` | Writes `jobs/unclear_<date>.md`: the jobs whose visa status stayed unclear, for `jd_extractor.py` - so they're processed like the rest |
| `visa_jobs_json.py <visa.md>` | Collects everything into `jobs/visa_jobs_<date>.json` |
| `job_report.py <json>` | Writes `JOB_RESULTS.md` (keeps a same-day `## Analysis` section when rebuilt; adds Resume / Judge links once tailored) |
| `build_resume.py --date <d>` | Builds resume + cover letter PDFs from Claude's `tailoring.json` files (tailor-resumes skill, step 5) |
| `tailor_all.py` | Alternative: the older Groq pipeline for all shortlisted JDs (slow on Groq's free tier) |
