# Step 3 - Full job descriptions (company site first, then LinkedIn)

## a. Run the extractor (background, about 30 seconds per job)

Check first that no other copy is running: `pgrep -fl jd_extractor`. Then run both lists, one after the
other (not at the same time):

```
.venv/bin/python jd_extractor.py jobs/jobs_<today>_<HHMM>_visa.md
.venv/bin/python jd_extractor.py jobs/research_<today>_sponsors.md
```

For each job it searches the web for the posting on the company's own site or its ATS (Greenhouse, Lever,
Ashby, Workday, SmartRecruiters, Personio, ...), opens it with Playwright, and saves it only if the page is
official (not an aggregator), its title matches, it names the job's city or country, and it's still open.
If no company page is found and the job is a LinkedIn listing, it reads the description from LinkedIn's
public job page instead - no login, a few seconds between requests; after two rate limits (HTTP 429) it
stops using LinkedIn for the rest of the run. Never log in to LinkedIn or use my account.
Each saved JD is scored against the resume right away:

- 60%+ -> `jobs/jd_visa/<today>/<Company>_<Title>_<City>.md`
- below 60% -> `jobs/jd_visa/<today>/skipped/`

Each file starts with the company, city, visa line, original listing, JD source, resume match, matched
and missing skills.

The scorer uses Groq's free tier; when all keys hit their cap the script waits and continues by itself.
Don't restart it - just wait.

## b. Find the ones the script missed

For each job marked ❌ in the script's output, search yourself: `"<company> <title> careers"`, the
company's careers page, and its ATS board (job-boards.greenhouse.io/<company>, jobs.lever.co/<company>,
jobs.ashbyhq.com/<company>, <company>.wd3.myworkdayjobs.com). Open found postings with Playwright (not
WebFetch), check the title, and save them in the same format in `jobs/jd_visa/<today>/`.
If the job is closed, or LinkedIn rate-limited the run and the posting isn't on the company site, leave it.

Then score the new files (cached ones are not re-scored):

```
.venv/bin/python job_match.py jobs/jd_visa/<today>
```

## c. Unclear-visa jobs - processed too

Jobs from companies with no public visa info (even after the deeper research) get the same treatment, so
good matches aren't missed:

```
.venv/bin/python unclear_visa_match.py jobs/jobs_<today>_<HHMM>_visa.md
.venv/bin/python jd_extractor.py jobs/unclear_<today>.md
```

The first writes the job list `jobs/unclear_<today>.md` (visa cell "unclear - confirm with recruiter");
the second extracts and scores their JDs into the same `jobs/jd_visa/<today>/` folder (60%+ kept,
below in `skipped/`). Run it after the other two extractor runs, not at the same time.

## d. Spot-check

Open 3 saved files: the description must be the real role text, not a cookie banner, a job list or a
different role. Fix or delete bad ones.

Status line: "Step 3 done - J JDs saved of K jobs (L from LinkedIn), S shortlisted 60%+ (U of them visa
unclear), M not found."
