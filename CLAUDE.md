# ATS resume parser - job hunt + tailored applications

Personal pipeline for Abhinav (Senior AI / GenAI / LLM engineer, based toward Berlin): find AI/ML jobs,
keep only visa-sponsoring companies, score each JD against the base resume, and write a tailored resume +
cover letter for the good matches. Everything runs from this folder with `.venv/bin/python`.

> The skills still name the old path `/Users/abhinav/Ats_resume_parser`. The real project root is the
> folder containing this file - always work here.

## Skills (entry points)

| Command | Skill | Does |
|---|---|---|
| `/job-hunt [notes]` | `.claude/skills/job-hunt/` | Daily run, last 24 hours, steps 1-6 below |
| `/job-hunt-custom <1d-4w> [notes]` | `.claude/skills/job-hunt-custom/` | Same pipeline over a chosen window (max 672h); skips jobs already in `applications/*/` or `jobs/jd_visa/*/`; lean mode for windows > 7 days |
| `/tailor-resumes [date]` | `.claude/skills/tailor-resumes/` | Step 5 on its own: resume + cover letter per shortlisted job |
| `/apply-jobs [date] [company\|retry]` | `.claude/skills/apply-jobs/` | Step 7, run by hand: applies in Chrome to the prepared `applications/<date>/*/` jobs only; unknown answers -> marked for my review |

Notes after a command (e.g. `only Berlin, Amsterdam`) are applied to the whole run
(`daily_jobs.py --cities Berlin Amsterdam`).

## Flow

```
1 find jobs      daily_jobs.py --hours H [--cities ...]   -> jobs/jobs_<date>_<HHMM>.md (+ jobs/jd/, jobs/daily/)
      |                                                       (drop jobs below 60% resume match)
2 visa check     sponsor_registers.py <list>               -> register hits (NL IND / UK / DK official, DE / ES weak)
      |          + Google question / web research           -> jobs/jobs_<date>_<HHMM>_visa.md, visa_research, research_<date>_sponsors.md
      |          yes | weak yes ⚠️ (both processed) | unclear (-> GPT) | dropped (says no, agency)
3 full JDs       jd_extractor.py <visa.md> (company site, else LinkedIn public page, no login)
      |          visa yes + weak yes; scored on save      -> jobs/jd_visa/<date>/ (60%+) or skipped/
      |          visa-unclear: no JD, list only            -> gpt_automation/company_list.txt (for GPT)
4 results        visa_jobs_json.py + job_report.py          -> JOB_RESULTS.md (+ ## Analysis written by Claude)
5 tailor         tailor-resumes skill: Opus writers -> build_resume.py -> Sonnet judges
      |          visa confirmed AND match >= 50%           -> applications/<date>/<Company>_<Title>_<City>/
6 cleanup        cleanup.py (dry run) then cleanup.py --yes; reply with funnel, shortlist, GPT list
7 apply (manual) /apply-jobs: Chrome, .env + apply_profile.yaml -> applications/<date>/<job>/application.json
```

Step details live in `.claude/skills/job-hunt/steps/1-...6-*.md` - edit those to change behaviour
(cities and roles: step 1; visa rules: step 2).

## Ground rules

- **Time window is exact.** 24h for `/job-hunt`, the given window for `/job-hunt-custom`. Never widen it.
- **LinkedIn separate** in every list and in the results. Never log in; stop LinkedIn after rate limits.
- **Visa: keep any hope.** Drop only an explicit "no", "must already have work rights", or agencies
  hiding the employer. Evidence keywords: visa, relocation, **expat** (expat package, 30% ruling), Blue Card.
- **Claude handles visa yes + weak yes (flagged ⚠️).** Only visa-unclear jobs (no evidence) go to GPT: Claude
  writes only `gpt_automation/company_list.txt` (+ `archive/company_list_<date>.txt`): company, job,
  city, evidence so far, posting link - no JD, score or resume. The user runs GPT on it from
  `gpt_automation/` (its own `CLAUDE.md`, `GPT_PROMPTS.md`, `base_resume/`; same rules as the automation). Only a job the user hands back gets step 3 e.
- **Honest scores.** Never make the scorer or judge more lenient, never pick a higher re-score.
- **Time-series resume version** (`resume_variants.json`, `ats_tailor/variants.py`) for forecasting-heavy
  JDs - real experience the base resume leaves out, not a kinder score.
- **One results file:** `JOB_RESULTS.md` (plus `gpt_automation/company_list.txt` for GPT). No other reports.
- **One copy of each script at a time** (`pgrep -fl <script>`); never delete `jobs/jd_visa/<today>/`
  mid-run.

## Apply rules (apply-jobs)

- Only jobs with a prepared folder in `applications/<date>/` (build.json + both PDFs). Answers only from `.env`,
  `apply_profile.yaml` (gitignored) and the job's folder - never guess; an unknown required answer = `needs_review`.
- Company site only: never LinkedIn Easy Apply, never log in, create accounts or type passwords. Submit once, never twice.

## Tailoring rules (tailor-resumes, `writer.md` / `judge.md`)

- Changes only: title (JD title), summary, ONE new company-fit project, cover letter. Experience,
  skills, education and other projects are untouched; **Think Tree** is never edited or moved.
- No company name anywhere in the resume or file names.
- **Common thread - Think Tree:** the summary always ends with a sentence on ThinkTree.AI, a non-profit
  AI learning platform used by NGO teachers to support students with ADHD; the cover letter's last
  paragraph tells the same story.
- **Cover letter = a story, 4 paragraphs, max 4 lines each:** intro tweaked to the JD -> motivation +
  company (fiancée lives in Berlin; for other cities they move there together) -> contribution (two real
  matching achievements) -> Think Tree + close. Must not read as AI-generated (banned phrases in
  `writer.md`). Paragraph 2 must contain "fiancée", "Berlin" and the job city, or `build_resume.py`
  inserts its own motivation sentence.
- Writer = Opus, judge = Sonnet (different models); the judge scores once, reported as is.

## Setup gotchas

- **`.env` is required** (not in git): `CANDIDATE_NAME`, `CANDIDATE_EMAIL` (and phone, location,
  LinkedIn), `GROQ_API_KEY` / `GROQ_API_KEYS` for the scorer, optional `PARTNER_TERM`, `PARTNER_CITY`,
  `RELOCATION_MOTIVATION`, `EXTRA_SKILLS`. Without it every score is "not scored" and
  `build_resume.py` fails (pydantic "Field required: candidate_name"). Settings: `ats_tailor/config.py`.
- Groq free tier: when keys hit their cap the scripts wait on their own - don't restart them.
- Long scripts (search, extraction) run in the background; wait for them before the next step.
- LaTeX engine for PDFs: `brew install tectonic`.

## Kept vs working files

Kept: `JOB_RESULTS.md`, `gpt_automation/`, shortlisted JD files it links, `applications/`, `companies.yaml`,
`jobs/seen.json`, `jobs/discovered_companies.yaml`, `jobs/visa_companies.json` (visa answer cache,
reused for 30 days), `resume_variants.json`, the base resume `Abhinav_kaushik_AI_ML.pdf`.
Everything else in `jobs/` and `outputs/` is working data removed by `cleanup.py`.
