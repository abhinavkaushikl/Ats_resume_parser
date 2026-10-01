# Step 2 - Visa check: fill the Visa column in the same file

Input and output are the **same file**: `jobs/jobs_<today>.md` from step 1. You edit the `Visa` cell of
every row in place and add the dropped companies at the bottom. Never write a second list
(no `_visa.md`, no `research_<date>_sponsors.md`, no JSON report).

Check once per company and country, not once per job - all rows of the same company in the same country
get the same tag.

## 0. Sponsor lists first (script, no tokens)

```
.venv/bin/python sponsor_registers.py jobs/jobs_<today>.md
```

It matches every company against the official registers (UK -> London, Dutch IND -> Amsterdam and the rest
of the Netherlands, Danish SIRI -> Copenhagen, Irish employment permits -> Ireland, Portuguese Tech Visa
certified companies -> Portugal) and the employer lists for Germany (Berlin, Munich, rest of Germany),
Spain (Barcelona), Sweden and Estonia (Switzerland, Italy and Luxembourg have no list - research them on
the web as usual), downloads them if older than 7 days, caches every listed company in
`jobs/visa_companies.json` and writes `jobs/register_hits_<today>.json`. Use it like this - don't research
what it already answered:

- **exact, official register** -> `visa`, source = the register. Done, no web search.
- **exact, DE / ES / SE employer list** -> `weak`. Germany is the main target: for every German job
  (Berlin, Munich, Germany) tagged weak, try one search for a stronger source (company careers page, the
  JD page, an official statement) to promote it to `visa`.
- **candidate** (similar name, e.g. "Amazon Science" vs "Amazon UK Services Ltd") -> decide by eye; one
  search only if unclear.
- **none** -> research as below. In London, not being on the register usually means no Skilled Worker
  sponsorship - check the legal entity name once before dropping it.

## a. Evidence, strongest first

1. **The posting page** says visa sponsorship / relocation / expat support is offered ("visa",
   "relocation", "expat package", "30% ruling", "Blue Card"), or not. Reading the visa line off a posting
   page you already have open is fine - but do **not** save, extract or score the job description.
2. **Official sponsor registers** (as above). A register hit never overrules the posting: if the ad says no
   sponsorship or existing work rights are required, drop it.
3. **The company's own** careers / benefits / FAQ pages (visa, relocation, expat, Blue Card).
4. **Third-party pages:** Relocate.me, Glassdoor, Make it in Germany, employee reviews.

Ignore US-only H-1B data. Reuse answers in `jobs/visa_companies.json` that are under 30 days old and have
a source link.

## b. Google question before tagging anyone `unknown`

Before leaving a company as unknown, ask Google the plain question:

```
Does <company> sponsor visa in <country>?
```

and read what Google shows (AI overview and top results). Use **Claude in Chrome**: load the
chrome-browser skill, open google.com in one new tab, do all searches there, close it at the end.
If Claude in Chrome is not connected, say so once in the status line and use web search with the same
question instead. Never try to get around Google's robot checks.

Note: in Germany, Poland and Austria no sponsor licence is needed, so a large tech employer hiring in
English is a reasonable `weak` only if some page actually says it hires internationally.

## c. Decide the tag

- `visa` - register, the posting, or the company's own page says sponsorship / relocation for foreigners.
- `weak` - evidence rests only on a third-party page, on an employer list (DE / ES / SE / EE), or on
  relocation support without a visa mention.
- `unknown` - nothing found after the Google question and the deeper round in (e).
- **dropped** - the company says it does not sponsor, the job requires existing work rights, or it is a
  recruitment agency / job board hiding the employer. Remove the row from its city table and list it in
  the bottom section instead.

## d. Write it into the file

Edit `jobs/jobs_<today>.md` in place:

- Each row's first cell becomes the tag, with the source link appended after it:
  `| visa · [IND register](https://...) | Acme GmbH | [Senior AI Engineer](url) | Berlin | ... |`
  For `weak`, write `weak · confirm with recruiter · [source](url)`. For `unknown`, write
  `unknown · checked: registers, careers page, Google` - no link needed.
- Keep the `| Visa | Company | Job | City | Opened | Link |` header, the `## <City> (n)` headings and the
  two parts (company sites, LinkedIn) exactly as they are - the register script parses them.
- Fill the `# Dropped - no sponsorship` section at the end of the file:

```
# Dropped - no sponsorship

## Says no sponsorship / residents only (n)
- Company (City) - reason · [source](url)
## Recruitment agency or job board - the real employer isn't named (n)
- Company (City)
```

- Update the counts line under the title: `N jobs · X visa · Y weak · Z unknown · D dropped`.
- Save every new answer to `jobs/visa_companies.json` (key `"<company>|<country>"`, with `visa`,
  `relocation`, `src`, `official`, `checked`) so the next run reuses it.

## e. Deeper research before settling on `unknown`

For every company still unknown, do a second, deeper round: the Google question again plus
company-specific searches (careers page, "visa", "relocation", "expat", "Blue Card", the national
register). Companies that turn out to sponsor are promoted to `visa` / `weak` in the same file; the rest
keep `unknown`. Don't research agencies or companies that already said no. Keep the evidence in
`jobs/visa_companies.json` - not in a separate research file.

Status line: "Step 2 done - N jobs tagged: X visa, Y weak, Z unknown, D dropped (R promoted by deeper research)."
