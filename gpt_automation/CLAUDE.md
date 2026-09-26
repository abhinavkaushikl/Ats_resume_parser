# Project: Company Job Extractor (GPT)

You process job postings for Abhinav Kaushik (Senior AI / GenAI / LLM engineer, Indian citizen, needs a
work visa; his fiancée lives in Berlin). The jobs are the ones whose **visa sponsorship is unclear** - no
evidence found yet. The main automation (Claude) handles confirmed and weak-evidence sponsors and
hands only these to you.

## Files

| File | Kind | What |
|---|---|---|
| `CLAUDE.md` | permanent | These instructions |
| `GPT_PROMPTS.md` | permanent | The prompts: 0 JD, 1 visa check, 2 match score, 3 resume + cover letter, 4 judge |
| `base_resume/base_resume.txt` | permanent | Base resume as text (use this) |
| `base_resume/Abhinav_kaushik_AI_ML.pdf` | permanent | The original resume PDF |
| `company_list.txt` | each run | The jobs to process (replaced every run) |
| `jd_scores_<date>.md` | each run (if present) | Claude's resume-match score per job (Prompt 2 already done), best first |
| `jds/<date>/` | each run (if present) | The full job descriptions for those jobs (Prompt 0 already done) |
| `archive/company_list_<date>.txt` | history | Earlier runs' lists |

`company_list.txt`: lines starting with `#` are comments. Every other line is one job:
`Company | Job | City | Source | What was checked | Link`
(Source = company site or LinkedIn; What was checked = the registers / searches that found nothing.)

## Command

**"Process the companies in company_list.txt"** - for every job line, in order, company by company
(one visa check per company and city, reused for its other jobs):

If `jd_scores_<date>.md` exists: use its JD files and scores - skip Prompt 0 and Prompt 2, and only
process jobs at 50%+ (check the listed blocker first; below 50% -> list under "Below 50%").

1. **Prompt 0 - JD.** Open the link, get the full job description. Closed / login wall / different
   role -> record it and skip the job.
2. **Prompt 1 - Visa.** Search for visa sponsorship, relocation and **expat** support ("expat package",
   "30% ruling", "Blue Card") for this company in this country. Use the JD's own sentences first.
   - `no` or `agency` -> stop for this company.
   - `yes` or `weak` -> continue. `unclear` -> stop, list it under "Unclear".
3. **Prompt 2 - Score** against `base_resume.txt` (time-series version from Appendix B if the JD is
   forecasting-heavy). Honest - never raise a score.
4. **Prompt 3 - Resume + cover letter** only if visa is `yes` / `weak` **and** score >= 50.
5. **Prompt 4 - Judge** the tailored resume, strictly, as a different reviewer.

## Rules

- Never log in to LinkedIn or any site. Public pages only.
- Never invent experience, numbers, degrees or skills; only what `base_resume.txt` shows (the one
  allowed addition: ThinkTree.AI is used by NGO teachers).
- Cover letter: exactly 4 short paragraphs (intro -> motivation + company with the fiancée / Berlin
  story -> contribution -> Think Tree + close). Resume summary ends with the Think Tree sentence.
- No company name in the resume itself. No em dashes, no "passionate", no "I am excited to apply".

## Output (one report per run)

`RESULTS_<date>.md`:

1. **Summary** - jobs processed, visa yes / weak / no / agency / unclear, JDs found, 50%+ count.
2. **Apply** table (visa yes / weak, score >= 50), best first:
   `Score | Company | Job | City | Visa (verdict + source) | Judge | Link`
   followed, per job, by the Prompt 3 JSON and the Prompt 4 JSON.
3. **Below 50%** - company, job, score, one-line reason.
4. **No sponsorship / agency** - company, city, evidence + source.
5. **Unclear** - company, city, what was searched.
6. **Skipped** - closed postings, login walls, wrong role.

A Prompt 3 JSON can be turned into PDFs by the main project: save it as
`applications/<date>/<Company>_<Title>_<City>/tailoring.json` and run `build_resume.py --date <date>`.
