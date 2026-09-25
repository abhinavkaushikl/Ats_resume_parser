---
name: tailor-resumes
description: Tailored resume + cover letter for every shortlisted job, written by Claude (no Groq) - for each job description in jobs/jd_visa/<date>/ Claude writes the new title, a tweaked summary and one new company-fit project, a script builds the LaTeX/PDF, and a separate Claude judge scores it. Use when the user asks to tailor / generate resumes for the shortlisted jobs, or runs /tailor-resumes; also step 5 of /job-hunt.
---

# Tailor resumes (Claude)

Project folder: `/Users/abhinav/Ats_resume_parser`. Date: today unless I give one (`/tailor-resumes 2026-09-25`).

Claude does the writing and the judging; `build_resume.py` does everything else (no LLM calls): it takes
the base resume, changes only the title, summary and one new project, renders the LaTeX template and
compiles the PDF. No Groq is used.

## Rules for every resume (subtle tailoring)

- **Changes:** title (the JD's job title), summary (tweaked toward the JD, clear), ONE new project fitting
  the company's profile, and the cover letter.
- **Never changes:** experience bullets, skills, education, the other projects. **Think Tree** (my free
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

**Which jobs get a resume (my rule).** Look at every JD `.md` file in `jobs/jd_visa/<date>/` **and** in
`jobs/jd_visa/<date>/skipped/` (not README/SHORTLIST) and read two header lines:
- **Visa confirmed:** the `Visa / relocation` line says `Visa: yes` and has no `⚠️` / "weak" / "unclear".
- **Resume match 50% or more** (the `Resume match` line) - note 50, not the 60% shortlist cut, so 50-59%
  jobs in `skipped/` count too.

Tailor only jobs that meet **both**. Do **not** tailor jobs whose visa is unsure (weak evidence ⚠️, or
unclear) - normally they have no JD at all (the job hunt only lists them in JOB_RESULTS.md under "Visa
unsure - waiting for your review"). Tailor one only when I have named it (then its JD is fetched and
scored first, job-hunt step 3 e, and it needs 50%+ like the rest). Jobs below 50% are never tailored.

For each job to tailor, the output folder is `applications/<date>/<file stem>/` (create it). Skip jobs
whose folder already has `build.json` unless I asked to redo them. Give me a status line: "N jobs to
tailor (visa confirmed, 50%+)".

### 2. Write (writer agents, parallel)

Split the jobs into batches of about 8 and start one writer agent per batch with the Agent tool,
`model: "sonnet"`, all in the same message so they run in parallel. Prompt for each (fill in the lists):

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
a title rejected by the seniority check or a trimmed bullet is fine; a company-name warning or a failed
build is not - fix that job's `tailoring.json` and run the command again (it only builds what's missing;
`--rebuild` rebuilds all).

### 4. Judge (judge agents, parallel)

Batches of about 10, one judge agent per batch with the Agent tool, `model: "haiku"` (never the writer's
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

Spot-check two resumes (`resume.txt`): no company name, Think Tree unchanged, only title / summary /
one new project differ from `_base_resume.txt`.

Reply with: how many resumes were made, a table (job, judge score, resume link), the lowest scores with
their main gap from `judge.json`, and any failures. Remind me that each folder has a `project_brief.md` to
prepare the new project if an interview comes.

## Files per job

`applications/<date>/<job>/`: `Abhinav_Kaushik_Resume.pdf`, `Abhinav_Kaushik_Cover_Letter.pdf`,
`project_brief.md`, plus working files (`tailoring.json`, `judge.json`, `resume.txt`, `build.json`, `.tex`).
