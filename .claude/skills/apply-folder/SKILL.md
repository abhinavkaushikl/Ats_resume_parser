---
name: apply-folder
description: Apply in Chrome to the jobs in gpt_automation/FINAL_413_CLEAN_APPLICATIONS/ - each numbered folder has job.md (company, job, location, apply link) plus resume.pdf and cover_letter.pdf. Opens the link, fills the form, uploads both PDFs, submits once, records application.json and moves applied folders to done/. Use when the user runs /apply-folder or asks to apply to the FINAL_413 folder jobs.
argument-hint: "[folder numbers or company, e.g. 238 240 | Reply] [live | auto]"
model: sonnet
---

# Apply to the FINAL_413 folders

Arguments: `$ARGUMENTS`. Root = `gpt_automation/FINAL_413_CLEAN_APPLICATIONS/` under the project root.
Rules are built with the user job by job - when a new kind of question comes up, ask, then add the answer here.

**Mode.** `live` (default until the user says otherwise): fill everything, screenshot, stop before Submit and
wait for "submit". `auto`: submit when every required answer is known and nothing is flagged.

## Which jobs

A folder is a candidate when it has `job.md`, `resume.pdf`, `cover_letter.pdf` and no `application.json`
with status `applied` / `submit_unconfirmed` / `skipped` (those are never redone; `needs_review` /
`needs_account` only on "retry"). Folders in `done/` are done.
**Order: folder number order, one by one (001, 002, 003 ...)** - not by score, unless the user names folders.

## Answers (only these sources - never guess)

- Name, email, phone, city, LinkedIn: `.env` via
  `.venv/bin/python -c "from ats_tailor.config import get_settings as g; s=g(); print(s.candidate_name, s.candidate_email, s.candidate_phone, s.candidate_location, s.candidate_linkedin_url)"`.
  Phone: country picker = India, then the number (type it; `form_input` on phone fields may keep only the prefix).
  Set the phone **before** the uploads (uploads scroll the page and coordinate clicks then miss); zoom to verify.
- Everything else: `apply_profile.yaml` (project root), matched by meaning.
- **Resume upload = the folder's `resume.pdf`; cover letter upload = `cover_letter.pdf`** (absolute paths,
  `file_upload` on the file input ref - never click the upload box). Check both file names show afterwards.
- **Preferred / work location question = the `Location` in `job.md`** (e.g. Munich), not Berlin by default.
  If that city is not an option, pick the closest listed option in the same country and flag it.
- **Salary:** a range in the JD / posting -> rule in `apply_profile.yaml` `salary.range_rule`; no pay anywhere
  -> `100000` (EUR, annual gross, plain number). Note in `answers_given` which rule was used.
- **Notice period:** 30 days. **Start date / when can you join** (no notice-period question): 15 Nov 2026.
- Work rights: honest - needs visa sponsorship, no EU work rights.
- Checkboxes in Recruitee questions: `ref` clicks may not tick them - click by coordinates, zoom to verify.
- Optional photo: leave empty. Optional diversity: profile default.
- Required question with no answer -> `needs_review` (exact label + options), don't submit.

## Skip before filling (read the JD first)

- **Regional language required** (German, Dutch, French, ... that the profile lacks): the JD calls it
  mandatory / required / must ("at least C1 German ... mandatory", "fluent German ... required") ->
  `skipped: mandatory_language`. Only "good / preferred / a plus / nice to have" -> apply, add a flag.
  English is never a reason to skip.
- Posting closed -> `skipped: posting_closed`.
- **LinkedIn links - Chrome must be logged OUT of LinkedIn.** If the page shows a signed-in LinkedIn (profile
  avatar, "Me" menu, feed nav), stop the whole run and ask me to log out - never browse LinkedIn signed in.
  Never sign in, never Easy Apply. On the public page:
  - `job.md` already has `Company apply link:` -> skip LinkedIn, go straight there.
  - "Apply" / "Apply on company website" -> read the link's href (`read_page` on it); LinkedIn wraps it in
    `linkedin.com/safety/go/?url=<company url>` - navigate to the decoded company URL. Save it in `job.md`
    as `- **Company apply link:** <url>` before filling.
  - Sign-in popup instead of a link -> close it, web-search `"<company> <job title>" -site:linkedin.com`,
    open the company posting, check title + city match `job.md`; none -> `skipped: no_company_link`.
  - Easy Apply only -> `skipped: linkedin_only`. "No longer accepting applications" -> `posting_closed`.
  - Pace: at most ~1 LinkedIn page per job, no rapid reloads. Two sign-in walls / "too many requests" in a
    row -> stop using LinkedIn for the rest of the run (web search only) and say so.
- Signup / login wall -> account hand-off exactly as in `.claude/skills/apply-jobs/SKILL.md` step 2b
  (`needs_account`; Claude never types a password).
- No CAPTCHA solving, no assessments.

## Per job (keep calls few: batch actions, read the form once, one screenshot before Submit)

1. Read `job.md`; open the apply link in the session's own tab; `get_page_text` for JD, salary, language.
2. Open the form (`Apply` / `Bewerben`, ignore "Apply with LinkedIn / Indeed / XING").
3. `find` all fields once; fill; upload both PDFs; answer questions by the rules above.
4. Screenshot the filled form. `live`: show the table of answers + flags, wait for "submit". `auto`: go on.
5. Click Submit **once**; wait ~6 s (Recruitee is slow), then read the page for a confirmation ("Thank you", "Bewerbung wurde eingesendet").
   None -> `submit_unconfirmed`, never click again.
6. Write `application.json` in the folder (format as in `apply-jobs` SKILL.md, plus `"flags": [...]`).
   `applied` -> move the folder to `done/` (`mkdir -p done && mv <folder> done/`). Other
   statuses stay in place.

Per-ATS tips: `.claude/skills/apply-jobs/ats_notes.md`.

## Reply at the end

Applied / needs your review (questions + options) / needs account / skipped (reason), one line each.
