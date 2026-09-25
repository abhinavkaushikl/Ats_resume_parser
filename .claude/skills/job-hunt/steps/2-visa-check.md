# Step 2 - Visa sponsorship check

Input: `jobs/jobs_<today>_<HHMM>.md` from step 1, minus the jobs the daily file skipped below 60%.
Check once per company and country, not once per job.

## a. Evidence, strongest first

1. **The job description** says visa sponsorship / relocation is offered, or not.
2. **Official sponsor registers:** UK Home Office register of licensed sponsors (London), Dutch IND
   recognised sponsors (Amsterdam), Danish SIRI fast-track list (Copenhagen).
3. **The company's own** careers / benefits / FAQ pages.
4. **Third-party pages:** Relocate.me, Glassdoor, Make it in Germany, employee reviews.

Ignore US-only H-1B data. Reuse answers in `jobs/visa_companies.json` that are under 30 days old and have
a source link.

## b. Google question before dropping anyone

Before removing a company for "no public info", ask Google the plain question:

```
Does <company> sponsor visa in <country>?
```

and read what Google shows (AI overview and top results). Use **Claude in Chrome**: load the
chrome-browser skill, open google.com in one new tab, do all searches there, close it at the end.
If Claude in Chrome is not connected, say so once in the status line and use web search with the same
question instead. Never try to get around Google's robot checks.

Note: in Germany, Poland and Austria no sponsor licence is needed, so a large tech employer hiring in
English is a reasonable "weak yes" only if some page actually says it hires internationally.

## c. Decide

- **Keep** if there is even slight public evidence: register, JD, company page, Google verdict,
  third-party page, relocation support. Mark it weak when it rests only on a third-party page or on
  relocation support without a visa mention.
- **Remove** only if: the company says it does not sponsor, the job requires existing work rights, or it's
  a recruitment agency / job board that hides the employer.
- Companies with no evidence after the Google question go in the "no public info" list.

## d. Write the visa file

Write `jobs/jobs_<today>_<HHMM>_visa.md` (same HHMM as the input). Format - the scripts parse it:

```
# AI / ML / Data Science jobs - last 24h - visa sponsorship checked

Source list: jobs_<today>_<HHMM>.md (...). Visa check run <today>.

**N jobs kept** (...) ...

## <City> (<n>)

| | Title | Company | Level | Location | Opened | Visa / Relocation | JD | Source |
|---|---|---|---|---|---|---|---|---|
<the job's row copied from the input file, with the Visa / Relocation cell replaced by:>
Visa: yes (<condition, if any>) · Relocation: yes / no / not stated · Source: [<name>](<link>)
<append " ⚠️ weak source, confirm with recruiter" for weak evidence>

... company-site jobs first, then a separate LinkedIn part ...

# Removed - no public visa info

## Says no sponsorship / residents only (n)
- Company (City) - reason
## Recruitment agency or job board - the real employer isn't named (n)
- Company (City)
## No public visa-sponsorship info found (n)
- Company (City)
```

The `Source list:` line, the `## <City> (` headings, the copied table rows (the `[JD](...)` link must stay)
and the `- Company (City)` lines must be exactly like this.
Save new answers to `jobs/visa_companies.json` (key `"<company>|<country>"`, with `visa`, `relocation`,
`src`, `official`, `checked`).

## e. Deeper research on the removed companies

For every company in "No public visa-sponsorship info found", do a second, deeper round: the Google
question again plus company-specific searches (careers page, "relocation", "Blue Card", the national
register). Save one entry per company and city (agencies and "says no" without searching) to
`jobs/visa_research_<today>.json`:

```json
[{"company": "...", "city": "...", "country": "...", "verdict": "yes|weak|no|unclear|agency",
  "note": "one line of evidence", "source": "https://..."}]
```

For every `yes` / `weak` company, copy its rows from the input file into
`jobs/research_<today>_sponsors.md` (same table format as the visa file, visa cell replaced by the verdict
and source, one `## <City> (n)` section per city).

Status line: "Step 2 done - K of N jobs kept (W weak), R added back by deeper research, X removed."
