# Step 3 - Reply

Nothing to clean up and nothing else to build: `jobs/jobs_<today>.md` is the whole deliverable.
Don't run `cleanup.py`, `visa_jobs_json.py` or `job_report.py`, and don't write `JOB_RESULTS.md`.

## a. Check the file

- Every row has a tag in the first cell (`visa`, `weak` or `unknown`) - no empty Visa cells left.
- The counts line matches the rows, and the dropped section lists the removed companies.
- LinkedIn jobs are still in Part 2, separate from the company-site jobs.

## b. Reply in the chat

- The funnel: jobs found -> `visa` / `weak` / `unknown` / dropped.
- The tag counts per city for `visa` + `weak` (a short table), so I can see where today's options are.
- The `visa` and `weak` jobs worth opening first, by title and company (title only - there is no score,
  so don't rank them as if there were). Max 10 lines, with their links.
- Anything that failed or was skipped, and why (e.g. Claude in Chrome not connected, a feed that errored).
- The link to `jobs/jobs_<today>.md` - the only file I need to open.
- One closing line: I pick jobs from the list, collect their job descriptions myself and hand them to you;
  then you run step 4 (`/tailor-resumes` or this skill's step 4) for the `visa` / `weak` ones.

Don't paste job descriptions and don't offer to fetch them.

Status line: "Step 3 done - jobs/jobs_<today>.md ready: X visa, Y weak, Z unknown."
