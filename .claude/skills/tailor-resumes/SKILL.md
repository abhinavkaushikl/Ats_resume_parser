---
name: tailor-resumes
description: Tailored resume + cover letter for every shortlisted job, written by Claude (no Groq) - for each job description in jobs/jd_visa/<date>/ Claude writes the new title (resume, current role and cover letter), a tweaked summary, JD-blended rewordings of experience bullets and one new company-fit project, a script builds the LaTeX/PDF, and a separate Claude judge scores it. Use when the user asks to tailor / generate resumes for the shortlisted jobs, or runs /tailor-resumes; also step 5 of /job-hunt.
model: sonnet
---

# Tailor resumes (Claude)

Project folder: `/Users/abhinav/Ats_resume_parser`. Date: today unless I give one (`/tailor-resumes 2026-09-25`).

Claude does the writing and the judging; `build_resume.py` does everything else (no LLM calls): it takes
the base resume, changes only the title, the current role's title, the summary, the reworded experience
bullets and one new project, renders the LaTeX template and compiles the PDF. No Groq is used.

## Rules for every resume (subtle tailoring)

- **Changes:** title (the JD's job title, in the resume and cover letter), the current (United Health
  Group) role's title by JD family (Data Scientist JD -> Senior Data Scientist, AI Engineer JD -> Senior
  AI Engineer, ML Engineer -> Senior Machine Learning Engineer), summary (tweaked toward the JD, clear),
  3-6 experience bullets reworded so the JD's words blend in naturally (same facts, same numbers, max 2
  lines - the build skips any edit that changes a number), ONE new project fitting the company's
  profile, and the cover letter.
- **Common thread - Think Tree:** the summary always ends with one sentence on ThinkTree.AI (non-profit
  AI learning platform used by NGO teachers to support students with ADHD), and the cover letter's last
  paragraph tells the same story.
- **Cover letter = a story in 4 short paragraphs** (each max 4 lines): intro tweaked to the JD ->
  motivation + the company (with the fiancée / Berlin story) -> contribution -> Think Tree + close.
  Details in `writer.md`. It must not read as AI-generated.
- **Experience version:** for a JD heavy on time series / forecasting, the build swaps in the fixed
  time-series bullets from `resume_variants.json` (Viavi: call / SMS handover forecasting with LSTM and
  XGBoost instead of the SLA bullet, plus the univariate AIOps KPI forecasting feature). These are my own
  words - writers never reword the variant bullets. The build picks the version from the JD the
  same way the scorer does; `"experience_variant"` in tailoring.json overrides it.
- **Languages:** "German: A1" is shown only for jobs in Germany / Austria / Switzerland or a JD that
  mentions German; elsewhere the section lists English only. The build decides this from the JD's
  Location line - writers do nothing.
- **Never changes:** other roles' titles, dates and companies, skills, education, the other projects. **Think Tree** (my free
  ADHD app, a charity tool) is never edited, trimmed or moved - the build keeps it first.
- **Invisible:** the company's name appears nowhere in the resume or in the file names, and no company
  product / brand words. The build also removes the name if it slips in.
- **Honest judge:** the judge is a different model from the writer and scores once; report the score as
  it is. Never re-write or re-judge a resume to get a higher number.

## Steps

### 1. Prepare

```
mkdir -p applications/<date>
.venv/bin/python resume_tailor.py --show-base > applications/<date>/_base_resume.txt
```

**Which jobs get a resume: every JD at the top of the folder.** Take every JD `.md` file directly in
`jobs/jd_visa/<date>/`, excluding `README.md`, `SHORTLIST.md`, `KEPT.md` and `VISA_MATCH.md`. A JD sitting
there is a job I kept, so it gets a resume.

**Never descend into the sub-folders.** `skipped/` (rejected by `/visa_match_score` - below the match cut,
or the JD refuses sponsorship), `no_jd_body/` (no job description to work from) and `deselected/` (I took
it off the list by hand) are all *out*. Building from them would produce applications I explicitly did not
want. Count the files first and tell me the number before you start writing.

**This skill does not judge whether a job is worth applying to.** Don't read the `Visa / relocation` or
`Resume match` header lines to decide anything, don't skip a JD for a low score, an `unclear` visa or a
missing score line, and don't re-check a visa or re-score a resume here. That is `/visa_match_score`'s
job, I run it first and I verify its report before starting this skill - so by the time you are tailoring,
the selection is already made. If a JD looks like a bad fit, build it anyway and say so in the final
reply, in one line.

Skip step 5 below unless `jobs/visa_jobs_<date>.json` exists - a hand-over run has no results file and no
`JOB_RESULTS.md`.

For each job, the output folder is `applications/<date>/<file stem>/` (create it). Skip jobs whose folder
already has `build.json` unless I asked to redo them. Give me a status line: "N jobs to tailor."

### 2. Write (writer agents, parallel)

Split the jobs into batches of about 8 and start one writer agent per batch with the Agent tool,
`model: "opus"` (always Opus - the resume and cover letter are what recruiters read), all in the same message so they run in parallel. Prompt for each (fill in the lists):

> Read `.claude/skills/tailor-resumes/writer.md` and follow it exactly. Base resume:
> `applications/<date>/_base_resume.txt`. For each job below, read the job description file and write
> `tailoring.json` into its folder. Jobs: `<jd file path> -> <output folder>` (one per line).
> Reply with one line per job: folder name, the title you used, the project name - nothing else.

Wait for all writers. Check every folder has a valid `tailoring.json` (`python -m json.tool`); rerun a
writer only for the missing ones.

### 3. Build

```
.venv/bin/python build_resume.py --date <date>
```

Builds the resume PDF, cover letter PDF, `resume.txt` and `project_brief.md` per job. Read its warnings:
a title rejected by the seniority check, a trimmed bullet or a skipped experience edit is fine
(the base bullet is kept); a company-name warning or a failed
build is not - fix that job's `tailoring.json` and run the command again (it only builds what's missing;
`--rebuild` rebuilds all).

### 4. Judge (judge agents, parallel)

Batches of about 10, one judge agent per batch with the Agent tool, `model: "sonnet"` (never the writer's
model), all in one message:

> Read `.claude/skills/tailor-resumes/judge.md` and follow it exactly. For each folder below, read
> `resume.txt` in the folder and the job description file, and write `judge.json` into the folder.
> Jobs: `<jd file path> -> <output folder>` (one per line). Reply with one line per job: folder, score.

Then refresh the index:

```
.venv/bin/python build_resume.py --date <date> --index
```

### 5. Results

If `jobs/visa_jobs_<date>.json` exists (a /job-hunt run), rebuild the results so JOB_RESULTS.md gets the
**Resume** and **Judge** columns (the Analysis section is kept):

```
.venv/bin/python job_report.py jobs/visa_jobs_<date>.json
```

Spot-check two resumes (`resume.txt`, and `experience_edits` in `build.json` for before/after): no
company name, Think Tree unchanged, the reworded bullets read naturally and keep their facts, and only
title / current role title / summary / reworded bullets / one new project differ from `_base_resume.txt`.

Reply with: how many resumes were made, a table (job, judge score, resume link), the lowest scores with
their main gap from `judge.json`, and any failures. Remind me that each folder has a `project_brief.md` to
prepare the new project if an interview comes.

## Files per job

`applications/<date>/<job>/`: `Abhinav_Kaushik_Resume.pdf`, `Abhinav_Kaushik_Cover_Letter.pdf`,
`project_brief.md`, plus working files (`tailoring.json`, `judge.json`, `resume.txt`, `build.json`, `.tex`).
