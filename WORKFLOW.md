# Daily job hunt - how to run it

One command runs the whole thing: find today's AI/ML jobs, keep the companies that sponsor visas, get the
full job descriptions, score each one against my resume (Abhinav_kaushik_AI_ML.pdf), and write a report
with analysis.

## Run it

1. Open the Claude desktop app, go to **Code**, and choose this folder (`/Users/abhinav/Ats_resume_parser`).
2. Type `/job-hunt` and press Enter (or just say "run the job hunt"). Optional notes go after it,
   e.g. `/job-hunt only Berlin and Amsterdam`.
3. Let it run (1-2 hours: job search, visa research, JD extraction and scoring). It posts a status line
   after each step.

For the Google visa questions it uses Claude in Chrome when it is connected (Chrome open, extension
installed, `/chrome` in the session); otherwise it falls back to web search and says so.

It's a Claude skill: [.claude/skills/job-hunt/SKILL.md](.claude/skills/job-hunt/SKILL.md) is the entry
point, and each step has its own prompt in `.claude/skills/job-hunt/steps/`:

| Step file | What it does |
|---|---|
| `1-find-jobs.md` | Discover companies, run the last-24h job search, first resume filter |
| `2-visa-check.md` | Visa evidence, the Google question, deeper research on removed companies |
| `3-job-descriptions.md` | Full JDs from company sites, else LinkedIn's public page (no login), scored |
| `4-results.md` | Build JOB_RESULTS.md and write the analysis |
| `5-tailor-resumes.md` | Tailored resume + cover letter + project brief for every shortlisted job |
| `6-cleanup-and-reply.md` | Delete working files, keep results, JDs and resumes, reply |

To change how a step works, edit its file - e.g. cities and roles in step 1, the 60% cutoff in
`job_match.py` (`MIN_MATCH`).

## What you get

**One file: [JOB_RESULTS.md](JOB_RESULTS.md)** - every visa-sponsoring job with company, link, resume
match score, matched and missing skills, the analysis and the top 5 to apply to. Open only this.

(The scripts also keep their working data in `jobs/` - job descriptions, the JSON, the visa research - you
don't need to open those.)

## The steps

1. **Find jobs** - last 24 hours only, 11 cities, AI/ML roles (`daily_jobs.py`). LinkedIn kept separate.
2. **Visa check** - JD, official sponsor registers, company pages, then the plain Google question
   "Does <company> sponsor visa in <country>?". Deeper research on every removed company.
3. **Job descriptions** - company site or ATS first, else LinkedIn's public page, no login (`jd_extractor.py`).
4. **Resume match** - honest 0-100 score per JD, 60%+ shortlisted (`job_match.py`).
5. **Results** - everything in JOB_RESULTS.md (`visa_jobs_json.py`, `job_report.py`) + written analysis.
6. **Tailored resumes** - for every shortlisted job, written by Claude: title + summary tweaked, one new project, a separate Claude judge scores it (`tailor-resumes` skill + `build_resume.py`). Also runs on its own: `/tailor-resumes`.
7. **Clean up** - deletes the working files; keeps JOB_RESULTS.md, the shortlisted JDs and `applications/`.

## Scripts

| Script | Does |
|---|---|
| `daily_jobs.py` | Last-24h jobs from company feeds + LinkedIn, resume-match filter |
| `jd_extractor.py` | Full JDs: company site (Playwright), else LinkedIn public page; scored on save |
| `job_match.py` | Resume vs JD score (cached in `outputs/.cache/`); `job_match.py <folder>` re-scores a JD folder and writes SHORTLIST.md |
| `unclear_visa_match.py` | Lists the unclear-visa jobs so they get JDs and scores too (60%+ kept, flagged) |
| `visa_jobs_json.py` | Builds `jobs/visa_jobs_<date>.json` |
| `job_report.py` | Builds `JOB_RESULTS.md` |
| `cleanup.py` | Deletes the day's working files (dry run by default, `--yes` to delete) |
| `build_resume.py` | Builds each tailored resume + cover letter PDF from Claude's `tailoring.json` (no LLM) |
| `tailor_all.py` | Alternative: the older Groq pipeline (slow on Groq's free tier) |
