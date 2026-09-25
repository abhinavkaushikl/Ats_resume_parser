# Step 4 - Results: JOB_RESULTS.md + analysis

Wait until nothing is still running: `pgrep -fl "jd_extractor|job_match|unclear_visa_match"` prints nothing.

## a. Build the results file

```
.venv/bin/python visa_jobs_json.py jobs/jobs_<today>_<HHMM>_visa.md
.venv/bin/python job_report.py jobs/visa_jobs_<today>.json
```

`JOB_RESULTS.md` (project root) now has: summary, shortlist 50%+ of the **visa-confirmed** jobs (company
sites and LinkedIn separately) with job link, visa + source, matched and missing skills and a link to the
saved JD file, the **"Visa unsure - waiting for your review"** table (company, job, city, visa evidence,
posting link - not scored), the below-50% list, the not-scored jobs, the visa research, and an
"Analysis data" section.

## b. Write the analysis

Insert a `## Analysis` section into JOB_RESULTS.md directly after the `## Summary` section. Base it on
the data: read `jobs/visa_jobs_<today>.json` and the JD files of the top matches - don't guess. Start with
one italic line saying how many jobs it is based on. Then:

- **What fits best** - which roles and companies match best, and the common thread across them.
- **What doesn't fit** - roles that score low and why (a low score is a real result, don't explain it away).
- **Recurring gaps** - gaps that come up across several good matches. Say which are real skill gaps and
  which may be wording: check the resume text first. Only suggest adding something if I really have that
  experience; never suggest claiming skills I don't have.
- **Visa unsure to review** - how many are waiting, by city; point out the ones whose titles look like
  the best fits (from the title only - they have no JD or score) so I can pick quickly.
- **Cities** - where today's best matches are.
- **Apply first** - top 5 visa-confirmed jobs in order, one line each on why.

Keep it short and honest.

Status line: "Step 4 done - JOB_RESULTS.md written: S shortlisted of N scored, V visa jobs."
