# Step 6 - Clean up and reply

Only after the resumes are done (step 5) and nothing is running
(`pgrep -fl "jd_extractor|job_match|daily_jobs|tailor_all"` prints nothing).

## a. Clean up

```
.venv/bin/python cleanup.py            # dry run: check the list first
.venv/bin/python cleanup.py --yes      # then delete
```

It deletes the day's working files (raw job lists, jobs/jd/, jobs/daily/, visa files, JSON, the
non-shortlisted JD files, skipped/, outputs/ caches, __pycache__, .DS_Store) and keeps JOB_RESULTS.md,
the shortlisted JD files it links to, applications/, code, the resume, .env, companies.yaml and the state
files (jobs/seen.json, jobs/discovered_companies.yaml, jobs/visa_companies.json). It refuses to run while
a job script is still running.

Then check that every `[JD](...)` and `[Resume](...)` link in JOB_RESULTS.md points to an existing file.

## b. Reply

Reply in the chat with:
- The funnel: jobs found -> after resume filter -> after visa check (+ added back by deeper research) ->
  JDs found -> shortlisted 60%+.
- The shortlist: match %, company, job (linked), city, visa (yes / weak), top matched and missing skills,
  judge score and a link to the tailored resume.
- The "Apply first" list and 2-3 lines of the analysis.
- The visa-unclear jobs matching 60%+, marked "visa unclear" (they're to apply to as well).
- Anything that failed or was skipped, and why (e.g. Claude in Chrome not connected, LinkedIn rate-limited).
- The link to JOB_RESULTS.md - the only file I need to open.

Don't paste job descriptions.
