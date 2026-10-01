# Step 4 - Tailor, only for the JDs I hand over

**Not part of the daily run.** Do this only when I give you one or more job descriptions - pasted in the
chat, dropped in a file, or named ("tailor the Acme one, JD below"). I pick the jobs from
`jobs/jobs_<date>.md` and collect their JDs myself; you never fetch one.

## a. Check the job is allowed

Find the job's row in `jobs/jobs_<date>.md`. Tailor it only if its tag is `visa` or `weak` (weak stays
flagged ⚠️ - I confirm with the recruiter). If the tag is `unknown`, say so in one line and tailor it
anyway only if I tell you to. Never tailor a dropped job unless I say the visa situation changed.

There is no resume score in this flow, so there is no 50% rule: a JD I hand over is a job I chose.

## b. Save the JD where the tailor skill reads it

For each JD, write `jobs/jd_visa/<date>/<Company>_<Title>_<City>.md` (`<date>` = today, or the list's date
if I name it). Keep the file layout the tailor skill and `build_resume.py` expect - the Location line
decides whether "German: A1" is shown, so it must be right:

```
# <Job title>

- **Company:** <Company>
- **City:** <City>
- **Location:** <City, Country>
- **Visa / relocation:** Visa: yes <⚠️ weak, confirm with recruiter, if weak> · Source: <register / page>
- **Original listing:** <posting URL from the job list>
- **Resume match:** not scored (job chosen by me)

## Job description

<the full JD text exactly as I gave it>
```

Paste my text as it is - don't summarise, shorten or rewrite it, and don't add anything I didn't give you.

## c. Tailor

Load the **tailor-resumes** skill and follow it for that date, with one difference: the job selection is
**the JDs I handed over** (the files you just wrote), not "visa yes and 50%+" - skip its scoring-based
selection rule and its step 5 (`job_report.py` / `JOB_RESULTS.md` - there is no results file in this
flow).

So, per job: Opus writer agent -> `tailoring.json` -> `.venv/bin/python build_resume.py --date <date>` ->
Sonnet judge agent -> `judge.json`. Writer and judge stay different models, the judge scores once and the
score is reported as it is. All the subtle-tailoring rules stay exactly as they are: only the title, the
current role's title by JD family, the summary, 3-6 reworded bullets and ONE new company-fit project
change; skills, education, other projects and Think Tree are untouched; no company name anywhere; the
cover letter is the 4-paragraph story with "fiancée" + Berlin + the job city in paragraph 2 and Think Tree
at the end.

Output per job: `applications/<date>/<Company>_<Title>_<City>/` with the resume PDF, the cover letter PDF
and `project_brief.md`.

## d. Reply

One table: job, company, judge score, link to the folder. Then the lowest judge score's main gap, and a
reminder that each folder has a `project_brief.md` in case of an interview. Don't rebuild any report file.

Status line: "Step 4 done - T resumes tailored from the JDs you gave me (judge median M/100), F failed."
