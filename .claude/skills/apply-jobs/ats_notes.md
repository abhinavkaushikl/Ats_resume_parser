# ATS notes (apply-jobs)

Short tips per applicant-tracking system. Detect it from the URL or the page footer.

| ATS | URL looks like | Notes |
|---|---|---|
| SmartRecruiters | `jobs.smartrecruiters.com/...` | "I'm interested" -> `oneclick-ui` "Easy Apply" page (SmartRecruiters' own form, fine - only LinkedIn Easy Apply is off-limits). Required: first/last name, email twice, City (autocomplete), Phone (country picker, +49 default), Resume. Fields sit in web components: `read_page`/`form_input` do not see them - click by screenshot coordinates and type. Ignore "Apply with LinkedIn / Indeed". Resume upload may autofill fields - check them afterwards. Screening questions come on a second step. |
| Greenhouse | `boards.greenhouse.io`, `job-boards.greenhouse.io`, `?gh_jid=` | One-page form, no account. Resume + cover letter "Attach" buttons (not "Enter manually"). Custom questions and EEO block at the bottom (EEO is optional). |
| Lever | `jobs.lever.co/...` | "Apply for this job" -> one page. Resume upload first, "Additional information" box can hold the cover letter text if no upload. |
| Ashby | `jobs.ashbyhq.com/...` | "Application" tab. One page, resume upload autofills. |
| Personio | `*.jobs.personio.de` / `.com` | One page, no account. Salary expectation and start date are often required - use the profile or `needs_review`. |
| Workable | `apply.workable.com/...` | One page, no account usually. |
| Zalando (own site) | `jobs.zalando.com/en/jobs/<id>` | "Apply" opens an inline form on the left; `find` sees every field. Required: name, email, country code + phone, start date (date input), salary (plain number), EU work-permit select, Zalando-employee select, sensitive-data checkbox. Resume + cover letter uploads. |
| Recruitee | `*.recruitee.com` | One page, no account. |
| Join.com | `join.com/companies/...` | Often asks to create an account -> `skipped: login_required`. |
| Workday | `*.myworkdayjobs.com` | Needs an account -> `skipped: login_required` unless already signed in. |
| SuccessFactors / Taleo / iCIMS | `career*.successfactors.*`, `taleo.net`, `icims.com` | Usually account + multi-step -> `skipped: login_required` unless already signed in. |
| Company's own site (e.g. Zalando) | company domain | Look for "Apply" -> often redirects to one of the above; treat it by the ATS you land on. |

General:
- Dropdowns: after selecting, read the field back - many ATS use custom selects where `form_input` does not stick;
  then click the option instead.
- Phone fields with a country picker: pick the country from the profile, then the number without the prefix.
- "How did you hear about us": profile `how_did_you_hear`.
- GDPR / privacy-policy consent checkbox required to submit: tick it (standard). "Keep my data for future
  roles / talent pool": profile `talent_pool_consent`.
