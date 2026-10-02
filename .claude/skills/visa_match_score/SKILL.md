---
name: visa_match_score
description: Rate the base resume against the job descriptions I handed over and tag each one for visa sponsorship - a report only, no resume is built. For every JD in jobs/jd_visa/<date>/ it fills the Visa / relocation and Resume match header lines and writes jobs/jd_visa/<date>/VISA_MATCH.md, then stops so I can verify. Use when the user runs /visa_match_score or asks to score / rate the shortlisted JDs or to check their visa status.
---

# Visa check + resume match score (report only)

Project folder: `/Users/abhinav/Ats_resume_parser`. Date: today unless I give one
(`/visa_match_score 2026-10-02`).

This skill answers two questions about the JDs I collected by hand, and **nothing else**:

1. **Does this company sponsor?** -> `Visa: yes` / `Visa: yes (⚠️ weak)` / `Visa: unclear`
2. **How well does my CURRENT resume fit this job?** -> an honest `0-100` score

It is deliberately separate from `/tailor-resumes`: rating a job and building an application are two
different tasks. This skill never writes a resume, a cover letter or a `tailoring.json`.

## Stop when the report is done

**Build the report, then stop.** I verify it myself and start `/tailor-resumes` when I am ready. Do not
run the tailor skill, do not load `writer.md`, do not create anything under `applications/`, and do not
offer to tailor at the end of the reply. A low score is information, not a decision - I decide.

## Ground rules

- **No Groq, and never `job_match.py`.** That script scores through `ats_tailor/llm.py`, which is a Groq
  client. Claude does the scoring here, in this session. Also never run `unclear_visa_match.py`,
  `jd_extractor.py`, `visa_jobs_json.py`, `job_report.py` or `tailor_all.py`.
- **Never fetch a JD.** The JD files already exist - I collected them. Read them from disk.
- **Honest score, scored once.** Report the number you get. Never re-score a JD to reach a nicer number,
  never soften the rubric, never pick the higher of two runs. A blocker keeps the score low even when
  much else matches.
- **Score the BASE resume, not a tailored one.** This is "how well do I fit this job today". It is not
  the `judge.md` score, which rates an already-tailored resume after the build. Two different numbers -
  never copy one into the other.
- **Visa: keep any hope.** `yes` on real evidence, `yes (⚠️ weak)` on slight evidence, `unclear` only
  when nothing is found. Say `no` only for an explicit refusal, a "must already have work rights", or an
  agency hiding the employer.
- **Edit the JD files in place.** No second copy of a JD anywhere.

## 1. Collect the JDs

```
ls jobs/jd_visa/<date>/*.md
```

Every `.md` except `README.md`, `SHORTLIST.md` and `VISA_MATCH.md`; include `skipped/` if it exists. From
each file read the `# <title>` line and the `**Company:**`, `**City:**` / `**Location:**` lines.

If that folder is missing, look for a differently named folder for the same date before giving up
(`jobs/Jd-<DD-MM-YYYY>/`, `jobs/jd_visa/<date>/`, anything I point you at) and say which one you used.
Don't move or rename my files; read them where they are.

If the folder does not exist or is empty, say so in one line and stop - there is nothing to rate. (I save
the JDs myself; `/job-hunt` step 4b writes them.)

### Refuse to score a stub

A file is only scoreable if it holds the **real job-description text** - the responsibilities and
requirements as the company wrote them. Check each file before scoring it and treat it as a stub if it

- is under ~1500 bytes, or
- says it does not contain the job description (e.g. "does **not** contain the full job-description body",
  an "Extraction Status" section), or
- has no requirements text at all - only a metadata block (Company / Location / Source / Opened).

**Never score a stub.** There is nothing to judge against, so any number would be invented. List the stubs
in the report under "Not scored - no job description", give them no score, and still tag their visa (the
company name is enough for that). If more than half the folder is stubs, say so in the **first line** of
the reply and ask me whether to go on - a folder of metadata copied out of `jobs/jobs_<date>.md` is not a
set of job descriptions, and rating it would produce 500 meaningless numbers.

A JD I pasted by hand is the real thing; a file generated from the job list is not.

Status line: "N JDs found for <date> - S scoreable, T stubs skipped."

## 2. Visa tag per JD

Strongest evidence first. Stop at the first one that answers.

1. **The JD text itself** - the file is already on disk, so read it. Look for `visa`, `sponsor`,
   `relocation`, `expat`, `30% ruling`, `Blue Card`, `work permit`, and for the opposite:
   "must already have the right to work", "no sponsorship", "EU citizens only". The JD outranks every
   register: if the ad refuses sponsorship, the tag is `no` even when the company is on a register.
2. **Official registers** - call `sponsor_registers.py`'s own API per company, so no job list is needed:

   ```
   .venv/bin/python -c "
   import importlib.util,sys
   s=importlib.util.spec_from_file_location('sr','sponsor_registers.py')
   m=importlib.util.module_from_spec(s); sys.modules['sr']=m; s.loader.exec_module(m)
   print(m.check('<Company>','<City>'))"
   ```

   An exact hit on an **official** register (UK / NL IND / DK SIRI / IE / PT) -> `yes`. An exact hit on a
   **DE / ES / SE / EE employer list** -> `yes (⚠️ weak)`. A `candidate` (similar legal name) -> decide by
   eye, one search only if unclear.

   Two results that are **not** evidence of anything: `None` means there is no register for that city at
   all (France, Belgium, Switzerland, Italy, Poland, Austria, Romania, Norway, Luxembourg, the Gulf, Asia),
   and `match: none` means the company is simply not on the list. Neither one is a "no" - carry on to the
   next source. In London a missing UK entry does usually mean no Skilled Worker sponsorship, so check the
   legal entity name once before you tag it.
3. **The visa answer cache** - `jobs/visa_companies.json`, entries under 30 days old with a source link.
4. **The company's own careers / benefits / FAQ page**, then third-party pages (Relocate.me, Glassdoor,
   Make it in Germany). Ignore US-only H-1B data - it says nothing about Europe.
5. **The Google question**, before settling on `unclear`:
   `Does <company> sponsor visa in <country>?` Use Claude in Chrome if it is connected (load the
   chrome-browser skill, one tab, close it at the end); otherwise say so once in the status line and use
   web search. Never work around a robot check.

Write the tag into the JD's header line, keeping the format `build_resume.py` and the tailor skill expect:

```
- **Visa / relocation:** Visa: yes · Source: <register / page>
- **Visa / relocation:** Visa: yes (⚠️ weak, confirm with recruiter) · Source: <page>
- **Visa / relocation:** Visa: unclear - checked: JD, registers, cache, Google
```

Save each new answer to `jobs/visa_companies.json` (key `"<company>|<country>"`, with `visa`,
`relocation`, `src`, `official`, `checked`) so the next run reuses it.

Status line: "Visa done - X yes, Y weak, Z unclear, D say no."

## 3. Resume match score per JD

Read the base resume once:

```
.venv/bin/python resume_tailor.py --show-base > /tmp/base_resume.txt
```

For a JD heavy on **time series / forecasting**, score against the time-series version of the experience
(`resume_variants.json`, `ats_tailor/variants.py`) - that is the resume that would actually be sent. Say
in the report which JDs were scored on the variant.

Then score each JD with the rubric in [scorer.md](scorer.md). Batch the JDs about 8 at a time into
parallel agents with the Agent tool, `model: "sonnet"`, all in one message; each agent writes
`match.json` next to its JD file. For 3 JDs or fewer, just do it yourself - no agents.

Prompt per agent:

> Read `.claude/skills/visa_match_score/scorer.md` and follow it exactly. Base resume:
> `/tmp/base_resume.txt`. For each JD below, read the file and write `match.json` beside it (same folder,
> `<jd stem>.match.json`). JDs: `<jd file path>` (one per line). Reply with one line per JD: file stem,
> score, the single biggest gap - nothing else.

Then write each score into the JD's header:

```
- **Resume match:** 72% - reasonable fit: <the one-sentence reason>
- **Matched:** <must-haves the resume shows>
- **Missing:** <must-haves it lacks>
- **Blockers:** <hard blockers, only if any>
```

Status line: "Scores done - median M/100, range L-H."

## 4. The report

Write `jobs/jd_visa/<date>/VISA_MATCH.md` - this is the file I open:

```markdown
# Visa + resume match - <date>

N JDs · visa: X yes, Y weak, Z unclear · match: median M/100

| JD | Company | City | Visa | Match | Biggest gap |
|---|---|---|---|---|---|
| [title](<jd file>) | Acme | Berlin | yes | 74% | no Kubernetes in production |

## Worth applying to first
<the ones that are visa yes/weak AND scored high - title, company, score, why>

## Weak visa - confirm with the recruiter
<company - what the evidence was>

## Low match - what is missing
<JD - the must-haves the resume does not show>
```

No other file. Do not touch `jobs/jobs_<date>.md` - that is the hunt's file.

## 5. Reply, then stop

- The funnel: N JDs -> visa yes / weak / unclear / no, and the match spread.
- The table from the report (or a short version of it) so I can see it without opening the file.
- Which JDs are scored on the time-series variant.
- Anything skipped or failed, and why (Claude in Chrome not connected, a JD with no company name, ...).
- The link to `jobs/jd_visa/<date>/VISA_MATCH.md`.
- One closing line: I verify this report and then run `/tailor-resumes <date>` myself for the jobs I
  want. **Do not start tailoring and do not offer to.**

Status line: "Report done - jobs/jd_visa/<date>/VISA_MATCH.md: X visa, Y weak, Z unclear, median match M/100."
