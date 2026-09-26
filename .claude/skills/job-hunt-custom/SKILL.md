---
name: job-hunt-custom
description: Job hunt over a time window I choose (1 day to 4 weeks) instead of the fixed last 24 hours - same pipeline as /job-hunt (find jobs, visa check, full JDs, score, JOB_RESULTS.md, tailored resume + cover letter). Use only when the user runs /job-hunt-custom or asks for a job hunt over a custom period like "last 2 weeks" or "last 10 days".
argument-hint: "<window: 1d-28d, e.g. 3d, 2w, 4w> [extra notes, e.g. only Berlin]"
model: sonnet
---

# Custom-window job hunt

Arguments: `$ARGUMENTS`

This is the **job-hunt** skill with a different time window. Read `.claude/skills/job-hunt/SKILL.md` and
follow it and its step files (`.claude/skills/job-hunt/steps/`) exactly, with only the overrides below.
Everything else - visa rules, honest scores, LinkedIn separate, one results file, cleanup - is unchanged.

## Overrides

1. **Time window.** Take it from the arguments: `Nd` = N days, `Nw` = N weeks (also "10 days", "2 weeks").
   Allowed range 1 day to 4 weeks (28 days); clamp anything larger to 28 days. If no window is given, ask me
   once, then run without further questions. Convert to hours (`HOURS = days * 24`, max 672).
   - This replaces the ground rule "Last 24 hours only": use exactly `HOURS`, never wider.
   - Step 1b: run `.venv/bin/python daily_jobs.py --hours <HOURS>` (add `--cities ...` if my notes limit cities).
   - Step 2: the visa file header reads `last <HOURS>h` instead of `last 24h`.
   - Wherever a step says "today's jobs", it means the jobs of this window. File names still use today's date.
2. **Skip jobs already handled.** A multi-week window overlaps earlier daily runs. Before step 2, drop every
   job that already has a folder in `applications/*/` (same company + title + city) or a JD file in
   `jobs/jd_visa/*/` from an earlier date, or is already listed in `gpt_automation/archive/company_list_*.txt` (sent to GPT earlier). Say how many were dropped in the step 1 status line.
3. **Keep it lean (bigger windows = many more jobs).** For windows over 7 days:
   - Step 2 deeper research: only for companies with no register hit and no cached answer, and at most
     one web search per company.
   - Step 1a: skip company discovery (no web searches) unless my notes ask for it - the known-company
     feeds and LinkedIn already cover the longer window.
   - LinkedIn older than a week is spotty; report the numbers as they are, don't re-query to fill gaps.
4. **Status lines** mention the window, e.g. "Step 1 done (last 14 days) - 640 jobs found, 212 already
   handled, 118 skipped below 60%".
