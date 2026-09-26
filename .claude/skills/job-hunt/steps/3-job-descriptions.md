# Step 3 - Full job descriptions (company site first, then LinkedIn)

**Visa yes and weak-yes jobs** (visa cell starts `Visa: yes`, with or without ⚠️) get a job description
and a score. The extractor skips visa-unclear jobs by itself - don't fetch, score or research their
JDs. They are listed in JOB_RESULTS.md for me to review; see "d. On request" below.

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

**Which resume version is scored.** `job_match.py` picks it per JD (`ats_tailor/variants.py`): a JD heavy
on time series / forecasting is scored against the **time-series version** from `resume_variants.json`
(Viavi Senior ML Engineer: SLA bullet -> call / SMS handover forecasting with LSTM and XGBoost, plus the
univariate AIOps KPI forecasting feature); every other JD against the base resume. If you score JDs
yourself (no scorer available), do the same: check the JD first, score a forecasting-heavy one against
the time-series version, and add `- **Resume version:** timeseries` to its header. Same strictness either
way - the version only adds real experience, it never makes the scoring kinder.

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

## c. Visa-unclear jobs - company list for GPT (no JDs)

Claude handles visa yes and weak-yes jobs. **Only visa-unclear jobs** (no evidence after the Google
question and the deeper research - not the weak ones) go to GPT, which I run myself from the `gpt_automation/`
folder (its own `CLAUDE.md`, `GPT_PROMPTS.md`, `base_resume/`). For them Claude does **not** fetch,
save, score or research the JD - it only writes the run's company list:

`gpt_automation/company_list.txt` (replace the previous one) and the same file as
`gpt_automation/archive/company_list_<today>.txt`. Format - GPT's `CLAUDE.md` depends on it:

```
# Company list - run <today> (<window>, <cities>)
# <N> jobs, <C> companies - visa unclear: no sponsorship evidence found yet.
# Evidence so far = <what was checked>
# Format: Company | Job | City | Source | What was checked | Link

<Company> | <Job title> | <City> | company site / LinkedIn | <one line: registers / searches that found nothing> | <posting URL>
...

# Not for processing (dropped: agency hiding the employer, or says no sponsorship):
# <Company> (<City>) - <reason>
```

One job per line, sorted by company, no `|` inside cells. The link is the original posting URL from
the job list (company ATS or LinkedIn job page), not a `jobs/jd/` file. Don't run
`unclear_visa_match.py` and don't run `jd_extractor.py` on these jobs. If `base_resume/` in
`gpt_automation/` is older than `Abhinav_kaushik_AI_ML.pdf`, refresh it (copy the PDF, and
`resume_tailor.py --show-base > gpt_automation/base_resume/base_resume.txt`).

## d. Spot-check

Open 3 saved files: the description must be the real role text, not a cookie banner, a job list or a
different role. Fix or delete bad ones.

## e. On request - a visa-unclear job I hand back

Only if I name a job from `gpt_automation/company_list.txt` and tell Claude to take it over (e.g. GPT found a
sponsor): run `.venv/bin/python jd_extractor.py jobs/jobs_<date>_<HHMM>_visa.md --only "<company>"`,
rebuild the results (step 4 a) and tailor it if it reaches 50%+.

Status line: "Step 3 done - J JDs saved of K visa-confirmed jobs (L from LinkedIn), S match 50%+ (W of them visa weak ⚠️), M not
found; U visa-unclear jobs written to gpt_automation/company_list.txt for GPT (no JDs)."
