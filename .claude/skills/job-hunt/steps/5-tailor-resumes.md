# Step 5 - Tailored resumes for every shortlisted job

Only after step 4 (JOB_RESULTS.md exists) and when no script is running.

Load the **tailor-resumes** skill and follow it for today's date. Its selection rule: tailor only jobs
with a **confirmed visa** (`Visa: yes`, no ⚠️ weak / unclear) **and a resume match of 50% or more**
(including 50-59% JDs in `skipped/`). Visa-unsure jobs have no JD or score (step 3) and are
not tailored - they're in JOB_RESULTS.md under "Visa unsure - waiting for your review"; when I name some,
follow step 3 e, then tailor those that reach 50%+. Run this step **before** cleanup (cleanup deletes
`skipped/`).

1. Claude writer agents (Sonnet) write the new title, the tweaked summary, one new company-fit project and
   the cover letter per job (`tailoring.json`).
2. `build_resume.py` builds the resume and cover letter PDFs from the base resume - experience, skills and
   Think Tree unchanged, no company name anywhere, no Groq.
3. Claude judge agents (Haiku, a different model from the writer) score each resume once.
4. `job_report.py` adds the **Resume** and **Judge** columns to JOB_RESULTS.md.

Output per job: `applications/<today>/<Company>_<Title>_<City>/` with the resume PDF, cover letter PDF and
`project_brief.md`.

(Alternative without Claude usage: `.venv/bin/python tailor_all.py` runs the older Groq pipeline in
subtle mode - slow on Groq's free tier.)

Status line: "Step 5 done - T resumes tailored (visa confirmed, 50%+; judge median M/100), W waiting for
your decision (visa unsure), F failed."
