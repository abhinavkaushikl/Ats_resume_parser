# ATS resume parser - job hunt + tailored applications

Personal pipeline for Abhinav (Senior AI / GenAI / LLM engineer, based toward Berlin): find AI/ML jobs,
keep only visa-sponsoring companies, score each JD against the base resume, and write a tailored resume +
cover letter for the good matches. Everything runs from this folder with `.venv/bin/python`.

> The skills still name the old path `/Users/abhinav/Ats_resume_parser`. The real project root is the
> folder containing this file - always work here.

## Skills (entry points)

| Command | Skill | Does |
|---|---|---|
| `/job-hunt [notes]` | `.claude/skills/job-hunt/` | Daily run, last 24 hours, steps 1-3 below: one tagged list, `jobs/jobs_<date>.md` |
| `/job-hunt-custom <1d-4w> [notes]` | `.claude/skills/job-hunt-custom/` | Same pipeline over a chosen window (max 672h); skips jobs already in `applications/*/` or `jobs/jd_visa/*/`; lean mode for windows > 7 days |
| `/visa_match_score [date]` | `.claude/skills/visa_match_score/` | Step 4: rates the JDs I handed over - visa tag + honest resume-match score into each JD header, report `jobs/jd_visa/<date>/VISA_MATCH.md`, then **stops**. Builds nothing |
| `/tailor-resumes [date]` | `.claude/skills/tailor-resumes/` | Step 5: resume + cover letter for **every** JD in `jobs/jd_visa/<date>/`. Gates on nothing - no visa check, no scoring |
| `/apply-jobs [date] [company\|retry\|accounts]` | `.claude/skills/apply-jobs/` | Step 5, run by hand: applies in Chrome to the prepared `applications/<date>/*/` jobs only; unknown answers -> marked for my review |

Notes after a command (e.g. `only Berlin, Amsterdam`) are applied to the whole run
(`daily_jobs.py --cities Berlin Amsterdam`).

## Flow

```
1 find jobs      daily_jobs.py --hours H [--cities ...]   -> jobs/jobs_<date>.md  (the ONLY file)
      |                                                      company | job | city | opened | link
      |                                                      no JD downloads, no scoring, no Groq
2 visa check     sponsor_registers.py jobs/jobs_<date>.md  -> register hits (NL IND / UK / DK / IE / PT
      |          + Google question / web research             official, DE / ES / SE / EE weak)
      |          tags written INTO the same file: visa | weak | unknown
      |          dropped (says no, needs work rights, agency) -> its "Dropped" section
3 reply          counts + the link to jobs/jobs_<date>.md. Nothing else is built or cleaned up.

-- then I collect the JDs of the jobs I want, by hand, and hand them to Claude --

4 rate (separate) /visa_match_score: for each JD in jobs/jd_visa/<date>/ - visa tag from the JD text
      |           itself + registers + cache + Google, and an honest 0-100 match of the BASE resume
      |           (Claude scores it, never job_match.py / Groq). Headers filled in place
      |           -> jobs/jd_visa/<date>/VISA_MATCH.md, then STOP. I verify it myself
5 tailor          /tailor-resumes (or /job-hunt step 4c): builds EVERY JD in the folder, no gate
      |           Opus writers -> build_resume.py -> Sonnet judges
      |                                                     -> applications/<date>/<Company>_<Title>_<City>/
6 apply (manual)  /apply-jobs: Chrome, .env + apply_profile.yaml -> applications/<date>/<job>/application.json
```

**Rating and building are two different tasks.** `/visa_match_score` decides *whether* a job is worth it
and stops; `/tailor-resumes` builds what I put in the folder and judges only its own output. The
`judge.json` score (tailored resume, after the build) and the `match.json` score (base resume, before it)
are different numbers - never copy one into the other.

Step details live in `.claude/skills/job-hunt/steps/1-...4-*.md` - edit those to change behaviour
(cities and roles: step 1; visa rules: step 2).

## Ground rules

- **Time window is exact.** 24h for `/job-hunt`, the given window for `/job-hunt-custom`. Never widen it.
- **One file, one place.** `/job-hunt` writes only `jobs/jobs_<date>.md` - steps 1 and 2 write that same
  file (step 2 fills the Visa column in place). No `JOB_RESULTS.md`, no `_visa.md`, no research file, no
  `gpt_automation/company_list.txt`, no second list anywhere.
- **No job descriptions, no scoring in the hunt.** Claude never fetches, saves or scores a JD in
  `/job-hunt`: the list carries the posting URL and I collect the JDs myself. Scoring happens only in
  `/visa_match_score`, on the JDs I handed over, and only in Claude's own head.
  `jd_extractor.py`, `job_match.py`, `unclear_visa_match.py`, `visa_jobs_json.py`, `job_report.py` and
  `tailor_all.py` are not used anywhere.
- **No Groq.** Nothing in the hunt, the rating or the tailoring calls Groq; `GROQ_API_KEY` is no longer
  needed. `job_match.py` is banned because it scores through `ats_tailor/llm.py`, which is a Groq client -
  `/visa_match_score` scores with Claude instead, using the same rubric (`visa_match_score/scorer.md`).
- **LinkedIn separate** in the list (Part 2) and in the reply. Never log in.
- **Visa: keep any hope.** Tag `visa` / `weak` on even slight evidence, `unknown` when nothing is found.
  Drop only an explicit "no", "must already have work rights", or agencies hiding the employer. Evidence
  keywords: visa, relocation, **expat** (expat package, 30% ruling), Blue Card.
- **Tailoring is on request only, and it gates on nothing.** A JD in `jobs/jd_visa/<date>/` is a job I
  chose, so it gets a resume + cover letter - whatever its visa tag or match score says. `/tailor-resumes`
  must not read those header lines to decide, and must not re-check or re-score anything.
- **Rating stops at the report.** `/visa_match_score` writes `VISA_MATCH.md` and stops: it never starts
  tailoring, never writes under `applications/`, and never offers to. I verify the report first.
- **Honest judge, honest scorer.** Never make either more lenient, never pick a higher re-score, and never
  re-run one to get a nicer number.
- **Time-series resume version** (`resume_variants.json`, `ats_tailor/variants.py`) for forecasting-heavy
  JDs - real experience the base resume leaves out, not a kinder score.
- **One copy of each script at a time** (`pgrep -fl <script>`); never overwrite a tagged
  `jobs/jobs_<date>.md` by re-running step 1 unless I ask.

## Apply rules (apply-jobs)

- Only jobs with a prepared folder in `applications/<date>/` (build.json + both PDFs). Answers only from `.env`,
  `apply_profile.yaml` (gitignored) and the job's folder - never guess; an unknown required answer = `needs_review`.
- Company site only: never LinkedIn Easy Apply. Signup/login walls -> Claude fills the non-secret signup
  fields, leaves the tab open and marks `needs_account`; I set the password (Chrome's password manager),
  CAPTCHA / email code, then `continue` or `/apply-jobs <date> accounts` finishes the job. Claude never types
  a password. Submit once, never twice.

## Tailoring rules (tailor-resumes, `writer.md` / `judge.md`)

- Changes only: title (JD title, resume + cover letter), the current role's title by JD family (Data
  Scientist JD -> Senior Data Scientist; AI Engineer JD -> Senior AI Engineer), summary, 3-6 experience
  bullets reworded so the JD blends in (same facts, same numbers, max 2 lines), ONE new company-fit
  project, cover letter. Skills, education, other projects and the time-series variant bullets are
  untouched; **Think Tree** is never edited or moved. "German: A1" appears only for German-speaking
  jobs (DE / AT / CH or a JD mentioning German) - `build_resume.py` drops it otherwise.
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
  LinkedIn), optional `SERPER_API_KEY` for company discovery, optional `PARTNER_TERM`, `PARTNER_CITY`,
  `RELOCATION_MOTIVATION`, `EXTRA_SKILLS`. Without it `build_resume.py` fails (pydantic
  "Field required: candidate_name"). Settings: `ats_tailor/config.py`.
- The job search runs in the background (about 10 minutes); wait for it before the visa check.
- LaTeX engine for PDFs: `brew install tectonic`.

## Kept vs working files

Kept: the dated job lists `jobs/jobs_<date>.md` (the deliverable), `applications/`, `companies.yaml`,
`jobs/seen.json`, `jobs/discovered_companies.yaml`, `jobs/visa_companies.json` (visa answer cache,
reused for 30 days), the JDs I hand over in `jobs/jd_visa/<date>/`, `resume_variants.json`, the base
resume `Abhinav_kaushik_AI_ML.pdf`. `cleanup.py` keeps `jobs/jobs_????-??-??.md` and removes the leftovers
of the old pipeline (`jobs/jd/`, `jobs/daily/`, visa files, JSON reports).
