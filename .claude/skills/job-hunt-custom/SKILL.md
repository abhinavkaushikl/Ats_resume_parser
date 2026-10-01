---
name: job-hunt-custom
description: Job hunt over a time window I choose (1 day to 4 weeks) instead of the fixed last 24 hours - same pipeline as /job-hunt (find jobs, tag each one visa / weak / unknown, all in the one dated file jobs/jobs_<date>.md; no JDs downloaded, nothing scored). Use only when the user runs /job-hunt-custom or asks for a job hunt over a custom period like "last 2 weeks" or "last 10 days".
argument-hint: "<window: 1d-28d, e.g. 3d, 2w, 4w> [extra notes, e.g. only Berlin]"
model: sonnet
---

# Custom-window job hunt

Arguments: `$ARGUMENTS`

This is the **job-hunt** skill with a different time window. Read `.claude/skills/job-hunt/SKILL.md` and
follow it and its step files (`.claude/skills/job-hunt/steps/`) exactly, with only the overrides below.
Everything else is unchanged: one file (`jobs/jobs_<today>.md`), visa tags written into that same file,
**no job descriptions and no scoring**, LinkedIn separate, tailoring only for the JDs I hand over.

## Overrides

1. **Time window.** Take it from the arguments: `Nd` = N days, `Nw` = N weeks (also "10 days", "2 weeks").
   Allowed range 1 day to 4 weeks (28 days); clamp anything larger to 28 days. If no window is given, ask me
   once, then run without further questions. Convert to hours (`HOURS = days * 24`, max 672).
   - This replaces the ground rule "Last 24 hours only": use exactly `HOURS`, never wider.
   - Step 1b: run `.venv/bin/python daily_jobs.py --hours <HOURS>` (add `--cities ...` if my notes limit
     cities). The file is still `jobs/jobs_<today>.md` and its title reads `last <HOURS>h`.
   - Wherever a step says "today's jobs", it means the jobs of this window.
2. **Skip jobs already handled.** A multi-week window overlaps earlier runs. Before step 2, drop every job
   that already has a folder in `applications/*/` (same company + title + city) or a JD file in
   `jobs/jd_visa/*/` from an earlier date, and every job that already appears in an earlier
   `jobs/jobs_<date>.md` with a `visa` / `weak` / `unknown` tag (reuse that tag instead of researching it
   again). Say how many were dropped in the step 1 status line.
3. **Keep it lean (bigger windows = many more jobs).** For windows over 7 days:
   - Step 2 deeper research: only for companies with no register hit and no cached answer in
     `jobs/visa_companies.json`, and at most one web search per company.
   - Step 1a: skip company discovery (no web searches) unless my notes ask for it - the known-company
     feeds and LinkedIn already cover the longer window.
   - LinkedIn older than a week is spotty; report the numbers as they are, don't re-query to fill gaps.
4. **Status lines** mention the window, e.g. "Step 1 done (last 14 days) - 640 jobs in
   jobs/jobs_<today>.md, 212 already handled and dropped".
