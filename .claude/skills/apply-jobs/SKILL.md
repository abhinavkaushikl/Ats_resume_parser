---
name: apply-jobs
description: Apply automatically to the jobs that are already prepared in applications/<date>/ (tailored resume + cover letter built) - opens each company apply page in Chrome, fills the form from .env + apply_profile.yaml, uploads the tailored PDFs and submits when every required answer is known; otherwise stops and marks the job for my evaluation with the reason. Use only when the user runs /apply-jobs or asks to apply to the prepared applications.
argument-hint: "[date, default today] [company filter, e.g. Redcare]"
model: sonnet
---

# Apply to prepared applications

Arguments: `$ARGUMENTS`. Project root = the folder containing `CLAUDE.md` (not the old
`/Users/abhinav/...` path). Date = today unless given. A company name in the arguments limits the run to it.

**Only prepared applications.** A job is applied to only if its folder `applications/<date>/<stem>/` has
`build.json`, `Abhinav_Kaushik_Resume.pdf` and `Abhinav_Kaushik_Cover_Letter.pdf`. Nothing else is ever
applied to - not JOB_RESULTS rows without a folder, not visa-unclear / GPT jobs, not jobs found on the page.

## Hard rules

- **Never guess.** Every answer comes from `.env`, `apply_profile.yaml` or the job's own folder
  (`resume.txt`, `tailoring.json`, cover letter). A required field with no known answer = stop, mark
  `needs_review`. Never invent salary, dates, legal declarations, years with a tool, or opinions.
- **Never log in, never create an account, never LinkedIn.** Already signed in (Chrome session) = fine.
  Login / signup / "create account" wall = `skipped`. LinkedIn Easy Apply or a LinkedIn-only path = `skipped`.
  Never type a password.
- **Never submit twice.** One click on the final Submit. If the result is unclear, mark
  `submit_unconfirmed` and leave the tab open - do not click again.
- **Honest answers** to work-rights questions: I need visa sponsorship and do not have EU work rights
  (as in the profile). Never tick a box that says otherwise to get past a filter.
- No CAPTCHA solving, no tests / assessments / video interviews - `needs_review`.
- `apply_profile.yaml` `do_not_apply` companies: fill nothing, `skipped: do_not_apply`.
- Avoid anything that opens a browser alert/confirm dialog. After 2-3 failed attempts at one step, stop that job
  (`skipped`, reason) and move on.

## 1. Select and preflight

```
.venv/bin/python - <date> <<'EOF'
import json, sys, pathlib
date = sys.argv[1] if len(sys.argv) > 1 else __import__("datetime").date.today().isoformat()
for d in sorted(pathlib.Path("applications", date).glob("*/build.json")):
    a = d.parent / "application.json"
    st = json.loads(a.read_text())["status"] if a.exists() else "pending"
    b = json.loads(d.read_text())
    print(f"{st:18} {d.parent.name} | {b.get('apply_url') or '-'} | {b.get('listing_url') or '-'}")
EOF
```
(replace `<date>`, e.g. `2026-09-26`). Take the `pending` ones, plus `needs_review` / `skipped` ones only
if I say "retry". `applied` and `submit_unconfirmed` are never redone.

Preflight, stop with a clear message if any fails:
- `.env` exists with `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `CANDIDATE_PHONE` (read them with
  `.venv/bin/python -c "from ats_tailor.config import get_settings as g; s=g(); print(s.candidate_name, s.candidate_email, s.candidate_phone, s.candidate_location, s.candidate_linkedin_url)"`).
- `apply_profile.yaml` exists. Empty values are fine (they just mean "unknown").
- Claude in Chrome is connected: load the tools in one ToolSearch call (`tabs_context_mcp, tabs_create_mcp,
  navigate, read_page, find, form_input, computer, file_upload, get_page_text, tabs_close_mcp`), then
  `tabs_context_mcp`.

Status line: "N prepared applications to apply (M already applied, K need review)".

## 2. Apply, one job at a time (new tab each, never reuse my tabs)

Read `ats_notes.md` (next to this file) once for per-ATS tips.

For each job:
1. **URL.** `apply_url` from `build.json`. If it is a LinkedIn URL, use `listing_url` only if that is not
   LinkedIn either; otherwise `skipped: linkedin_only`. Open it in a new tab.
2. **Page check.** Posting closed / 404 -> `skipped: posting_closed`. Click the Apply button (company's own
   form). If the only way is "Apply with LinkedIn/Easy Apply", `skipped: linkedin_only` ("Apply with
   LinkedIn" autofill buttons: ignore, use the manual form). Login/signup wall -> `skipped: login_required`.
3. **Read the whole form first** (all steps/pages if you can see them) and map every field to an answer:
   - Name, email, phone, location, LinkedIn -> `.env`.
   - Resume upload -> `Abhinav_Kaushik_Resume.pdf`; cover letter upload -> `Abhinav_Kaushik_Cover_Letter.pdf`
     (absolute paths in the job folder, `file_upload`). A cover-letter text box -> the paragraphs from
     `tailoring.json` `cover_letter` (greeting + paragraphs + sign-off), not rewritten.
   - Standard questions -> `apply_profile.yaml` (match by meaning: "Do you require sponsorship?" =
     `needs_visa_sponsorship`). Select the option whose text matches the profile value; if no option matches
     clearly, the field is unknown.
   - Current employer / title / education / years of experience -> `resume.txt` of this job.
   - **Salary:** look for a pay range in `job_description.md` and on the posting page. Range found -> the
     top of the range (e.g. 90,000-95,000 -> `95000`). None -> `salary.expectation_yearly` (100000). Annual
     gross, plain number unless the field asks otherwise; note in `answers_given` which rule was used.
   - **Start date** always `availability.earliest_start_date` (15 Nov 2026), **notice period** 30 days.
   - Optional fields with no answer: diversity -> profile `diversity` default; others blank.
   - **Required field with no answer -> unknown.** Also unknown: open questions that need my own opinion or a
     new text ("Why do you want to work here?" is fine only by reusing cover letter paragraph 2 verbatim;
     anything else -> unknown), legal/consent declarations beyond a standard
     privacy-policy / data-processing checkbox.
4. **Any unknown required field -> stop.** Do not fill half and submit. Leave the tab open, record every
   unknown question (exact label + options) as `needs_review`.
5. **Fill** everything, upload both PDFs, check the uploads show the file names. Take a screenshot of the
   filled form and read it back (`read_page`) to verify the values stuck (dropdowns especially).
6. **Submit** once. Wait, then look for a confirmation ("Thank you", "application received", a
   confirmation page/email notice). Found -> `applied`, copy the confirmation text. Not found / error shown
   -> `submit_unconfirmed` with what the page says; leave the tab open. Close the tab only after `applied`.

## 3. Record

Write `applications/<date>/<stem>/application.json` right after each job (before the next one):

```json
{
  "status": "applied | needs_review | skipped | submit_unconfirmed",
  "reason": "one line, e.g. 'required question: expected salary (no value in apply_profile.yaml)'",
  "questions_unanswered": [{"label": "...", "type": "select|text|checkbox", "options": ["..."]}],
  "answers_given": {"<field label>": "<value>"},
  "files_uploaded": ["Abhinav_Kaushik_Resume.pdf", "Abhinav_Kaushik_Cover_Letter.pdf"],
  "url_used": "https://...",
  "ats": "smartrecruiters | greenhouse | lever | personio | ashby | workday | company | other",
  "confirmation": "text of the confirmation message, if applied",
  "timestamp": "2026-09-26T10:30"
}
```

Then refresh the results file (the Apply column shows the status):
`.venv/bin/python job_report.py` - only if a `jobs/visa_jobs_*.json` for that date still exists; if cleanup
already removed it, leave JOB_RESULTS.md as is and say so.

## 4. Reply

- **Applied (N):** company - job - city - ATS - confirmation (one line each).
- **Needs your evaluation (N):** company - job - reason - the exact unanswered questions with options - link
  (tab left open).
- **Skipped (N):** company - job - reason (linkedin_only, login_required, posting_closed, ...).
- Offer: "Tell me the answers and I'll add them to `apply_profile.yaml`, then `/apply-jobs retry` finishes
  them." Add only what I actually answer; a job-specific answer goes under `per_company` in the profile.
