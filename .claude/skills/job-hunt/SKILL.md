---
name: job-hunt
description: Daily AI/ML job hunt for Abhinav - find every job posted in the last 24 hours and tag each one for visa sponsorship (visa / weak / unknown), all in ONE dated Markdown file, jobs/jobs_<date>.md. No job descriptions are downloaded and nothing is scored; Abhinav collects the JDs himself and hands them over, and only then is a tailored resume + cover letter written (visa or weak jobs). Use when the user asks to run the job hunt, fetch today's jobs, or runs /job-hunt.
model: sonnet
---

# Daily job hunt

Run the whole job hunt in this project folder (`/Users/abhinav/Ats_resume_parser`) without asking me
questions along the way. If I added notes when starting (e.g. "only Berlin and Amsterdam"), apply them.

**What I want: ONE file, `jobs/jobs_<today>.md`.** Every job posted in the last 24 hours with company
name, job title, city, posting time and the posting URL - and a visa tag per job:

| Tag | Meaning |
|---|---|
| `visa` | sponsors (register, JD, company page) |
| `weak` | some evidence only, confirm with the recruiter |
| `unknown` | nothing found after the Google question and deeper research |
| dropped | says no, requires existing work rights, or an agency hiding the employer - bottom section |

**Your job stops there.** Do **not** download, fetch, extract or score job descriptions - that is not
your job, I do it by hand. No `jd_extractor.py`, no `job_match.py`, no scoring, no Groq, no
`JOB_RESULTS.md`, no `gpt_automation/company_list.txt`, no second list anywhere. One file per day, in
`jobs/`, with the date in its name.

**Tailoring happens later, only when I hand you a JD** (step 4): I paste or save the job description of a
job I picked from the list, and you tailor the resume + cover letter for it exactly as before
(`applications/<date>/`). Only `visa` and `weak` jobs are tailored.

## How to run

Do the steps in order. Before each step, read its file in `steps/` and follow it exactly. After each step,
give me one status line (e.g. "Step 2 done - 88 of 261 jobs tagged visa, 40 weak, 90 unknown").

1. [steps/1-find-jobs.md](steps/1-find-jobs.md) - find the last 24 hours' jobs, write the one dated file
2. [steps/2-visa-check.md](steps/2-visa-check.md) - fill the Visa column in that same file
3. [steps/3-reply.md](steps/3-reply.md) - reply with the counts and the link to the file
4. [steps/4-tailor-on-demand.md](steps/4-tailor-on-demand.md) - **only when I hand over a JD**, not part of the daily run

The job search runs in the background (about 10 minutes); wait for it before step 2.

## Ground rules (whole run)

- **Last 24 hours only.** Never widen the time window.
- **One file, one place.** `jobs/jobs_<today>.md`. Steps 1 and 2 write the same file - step 2 edits the
  Visa column in place, it never creates a second list. No other report, anywhere.
- **No job descriptions.** Never fetch, save, summarise or score a JD. The list has the posting URL; that
  is all I need. Never run `jd_extractor.py`, `job_match.py`, `unclear_visa_match.py`, `visa_jobs_json.py`,
  `job_report.py` or `tailor_all.py` in this skill.
- **No Groq.** Nothing in this skill calls an LLM scorer. `GROQ_API_KEY` is not needed any more.
- **LinkedIn separate.** LinkedIn jobs stay in their own part of the file. Never log in to LinkedIn.
- **Visa: keep any hope.** Tag `visa` or `weak` on even slight public evidence; `unknown` when nothing is
  found. Drop only an explicit "no", "must already have work rights", or an agency hiding the employer.
- **Don't destroy the file.** Never delete or overwrite `jobs/jobs_<today>.md` once step 2 has tagged it;
  re-running step 1 on the same day rewrites it, so only do that if I ask. Only one copy of
  `daily_jobs.py` at a time - check `pgrep -fl daily_jobs` before starting it.
- If a step fails, say what failed and why, continue with what you have, and list it in the final reply.

## Scripts (project root, run with `.venv/bin/python`)

| Script | Does |
|---|---|
| `daily_jobs.py --hours 24 [--cities ...]` | The only search script: company feeds + LinkedIn's public search, last 24h, writes **only** `jobs/jobs_<today>.md` (company, job, city, opened, link; empty Visa column). No JD downloads, no scoring. |
| `sponsor_registers.py jobs/jobs_<today>.md` | Step 2 first: matches every company against the official registers (UK / NL IND / DK / IE / PT) and the DE / ES / SE / EE employer lists (auto-downloaded weekly to `jobs/registers/`), caches hits in `jobs/visa_companies.json` |
| `build_resume.py --date <d>` | Step 4 only: builds resume + cover letter PDFs from Claude's `tailoring.json` files |

Everything else in the root (`jd_extractor.py`, `job_match.py`, `visa_jobs_json.py`, `job_report.py`,
`tailor_all.py`) is **not** used by this skill.
