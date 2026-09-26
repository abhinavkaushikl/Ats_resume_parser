# Job-application prompts (GPT-ready)

These are the same rules the Claude automation uses, rewritten so they work on their own in GPT.
Use them in order for each job:

0. **Job description** - open the posting link and pull out the full JD.
1. **Visa check** - is the company likely to sponsor a visa for this city?
2. **Match score** - honest 0-100 fit of the JD to the resume.
3. **Resume + cover letter** - only if visa = yes and score >= 50.
4. **Judge** - a strict recruiter scores the tailored resume (use a different chat / model than step 3).

For every prompt paste: the prompt, then the job's details / JD where it says `<<< ... >>>`, and the
**base resume** from `base_resume/base_resume.txt`. The jobs come from `company_list.txt`.

---

## Prompt 0 - Get the job description

```
Open this job posting and give me the full job description as plain text: title, company, location,
the complete role text (responsibilities, requirements, nice-to-haves, benefits) exactly as written -
no summary, no rewording. Also say whether the posting is still open, and quote any sentence that
mentions visa, sponsorship, relocation, expat support, 30% ruling, Blue Card, or "right to work".
If the page is closed, a login wall or a different role, say so and stop.

Link: <<< link >>>
```

---

## Prompt 1 - Visa sponsorship check

```
You are researching whether a company sponsors work visas for a non-EU candidate (Indian citizen,
Senior AI/ML engineer) for a job in a specific city. Search the web.

Company: <<< company >>>
City / country: <<< city, country >>>
Job title: <<< title >>>
Job link: <<< link >>>

Evidence, strongest first:
1. The job description itself says visa sponsorship / relocation / expat support is offered ("visa",
   "relocation", "expat package", "30% ruling", "Blue Card") - or says it is not.
2. Official sponsor registers: Dutch IND public register of recognised sponsors (Netherlands), UK Home
   Office register of licensed sponsors (UK), Danish SIRI fast-track list (Denmark).
3. The company's own careers / benefits / FAQ pages (visa, relocation, expat, Blue Card, "we sponsor").
4. Third-party pages: Relocate.me, Glassdoor, Make it in Germany, employee reviews.
Also ask the plain questions "Does <company> sponsor visa in <country>?" and "<company> relocation expat
<country>" and read the top results.
Ignore US-only H-1B data. In Germany no sponsor licence is needed (EU Blue Card): a large tech employer
hiring in English counts as a weak yes only if some page actually says it hires internationally.

Decide:
- yes    - register listing, the JD, or an official company page says so.
- weak   - only a third-party page, or relocation / expat support without a visa mention.
- no     - the company or JD says it does not sponsor, or the job needs existing work rights.
- agency - a recruitment agency / job board that hides the real employer.
- unclear - nothing found after the searches.
Keep any hope: choose weak over unclear if there is even slight public evidence.

Answer in exactly this format:
Verdict: yes | weak | no | agency | unclear
Relocation / expat support: yes | no | not stated
Evidence: <one line>
Source: <best URL>
```

---

## Prompt 2 - Match score (honest, 0-100)

Use the **time-series version** of the resume (Appendix B) when the JD is heavy on time series /
forecasting (forecasting in the title, or forecasting terms clearly outweigh LLM / GenAI terms).

```
You are an experienced technical recruiter. Judge how well the candidate's CURRENT resume fits the
job description, as an honest 0-100 match. Judge only real evidence in the resume; do not assume skills it
does not show, and do not give credit for something the candidate could learn.

Weigh, in this order:
1. Must-have requirements (core skills, tools, domain, years and level of experience) - most of the score.
2. The kind of work: does the candidate's actual experience look like this job's day-to-day work?
3. Nice-to-have requirements - a little.
Hard blockers (a required language the resume does not show, a required degree or clearance it lacks, a
completely different field) keep the score low whatever else matches.

Scale: 85-100 strong fit, most must-haves clearly shown · 70-84 good fit, a few gaps · 60-69 reasonable
fit, worth applying · 40-59 partial fit, important gaps · 0-39 poor fit or different role.

Return JSON: {"score": int, "matched": [must-haves the resume shows], "missing": [must-haves it lacks],
"blockers": [hard blockers, if any], "reason": "one sentence"}

CANDIDATE RESUME:
<<< paste base_resume/base_resume.txt (with Appendix B applied if forecasting-heavy) >>>

JOB DESCRIPTION:
<<< paste JD >>>
```

---

## Prompt 3 - Tailored resume changes + cover letter

```
You tailor Abhinav's resume to one job description. You write ONLY four things: the title, the summary,
one new project, and the cover letter. Everything else in the resume (experience, skills, education,
other projects) stays exactly as it is - never rewrite it.

Inputs: the BASE RESUME and the JOB DESCRIPTION below. Company: <<< company >>>, City: <<< city >>>.

GOAL
The resume must get shortlisted for THIS job while reading like Abhinav's normal resume. A recruiter must
not be able to tell it was written for their company.

TITLE
The JD's job title exactly as the JD writes it, without gender tags "(m/f/d)", locations or team names,
e.g. "Senior Machine Learning Engineer". If the JD title claims more seniority than the resume shows
(Staff, Principal, Lead, Head), keep the base title "Senior AI Engineer".

SUMMARY
3-4 sentences, 60-90 words. Start from the base summary and re-aim it at this job: lead with the
experience that matters most for the JD, use the JD's own words for work Abhinav really did, end with
what he brings. Clear, plain, confident.
- Only what the resume shows: no new domains, years of experience, degrees, certifications or numbers
  that aren't in the base resume.
- No company name, no product names, no "passionate about <company>".
- Always END with the Think Tree sentence, e.g. "Alongside this, I am building ThinkTree.AI, a
  non-profit AI learning platform used by NGO teachers to support students with ADHD." Keep its meaning
  fixed (non-profit, used by NGO teachers, students with ADHD); wording may flex. It counts toward the
  60-90 words.

NEW PROJECT (the main lever)
One project that fits the company's profile and closes the JD's biggest gaps, built from techniques the
base resume already shows (so Abhinav can prepare and explain it).
- name: 2-5 plain words describing what it does, like a normal portfolio project ("Delivery Demand
  Forecasting Engine"). Never the company's name or product names.
- bullets: exactly 2, one sentence each, 20-30 words, past tense, starting with a verb.
  (1) what was built, for which problem, with the core method; (2) how it was evaluated and served.
  Describe the problem at industry level ("demand forecasting for last-mile delivery"), not the
  company's own product. Use the JD's technologies where they fit the work.
  No numbers, percentages or scale words (millions, daily).
- technologies: 5-8 items, the JD's tool names first where they fit.
- Only technically possible claims: closed models (Claude, GPT-4, Gemini) are used via API with
  prompting / RAG / tools, never "fine-tuned"; fine-tuning is for open models (Llama, Mistral, BERT).

EXPERIENCE VERSION
- "timeseries" when the JD is heavy on time series / forecasting (forecasting in the title, or the
  must-haves are mostly forecasting rather than LLM / GenAI). Then the Viavi SLA bullet is replaced by
  "Developed time-series forecasting of base-station call handover and SMS handover volumes using LSTM
  and XGBoost." and "Developed a forecasting feature for the AIOps monitoring product, forecasting
  univariate KPIs across the network." is added. Write the summary forecasting-first.
- "base" otherwise.

COVER LETTER
The letter tells ONE story, told by a person, not a list of qualifications. It MAY name the company and
role. Exactly 4 paragraphs, in this order, each at most 4 lines on the page (about 45-65 words, 2-3
sentences), about 200-250 words in total:
1. Introduction (tweaked to the JD). Who Abhinav is, in the JD's framing: the role he is applying for
   and the part of his experience closest to what this JD needs most. One line on the thread that ties
   his work together.
2. Motivation and the company. Why this company and why this city, told as his story: what the company
   does and why that work matters to him, then the personal reason: his fiancée lives in Berlin; for a
   Berlin job he is building his career in the city where they are making their home; for any other
   city they plan to move to <job city> together and settle there long term. Use the words "fiancée",
   "Berlin" and the job's city. No flattery ("industry leader", "renowned").
3. Contribution. What he would bring to this team, backed by two concrete things he has really done that
   match the JD's main needs. With the "timeseries" version, lead with the forecasting work: call / SMS
   handover forecasting for base stations (LSTM, XGBoost), the univariate KPI forecasting feature in the
   AIOps monitoring product, and the Holt-Winters demand forecasting across 500+ network devices; don't
   mention the SLA system then.
4. Social cause and close. Think Tree - the same thread as the resume summary: he is building
   ThinkTree.AI, a non-profit AI learning platform used by NGO teachers to support students with ADHD,
   and what it says about how he builds (for real users, carefully). Then one plain closing line
   inviting a conversation.
Story, not template: each paragraph leads into the next (intro -> why here -> what I'd do -> who I am
beyond work). Vary sentence length; no bullet-like sentences strung together; no paragraph that could be
pasted into any other company's letter. Only numbers that appear in the base resume. Banned: "I am
excited to apply", "I am writing to express", "passionate", "thrilled", "I believe I would be a great
fit", "leverage", "cutting-edge", "dynamic", "fast-paced", "Furthermore", "Moreover", "In conclusion",
em dashes. Don't repeat the resume's bullets word for word.

STYLE FOR EVERYTHING
Write like a person: plain words, no buzzword chains, no "leveraged", "spearheaded", "cutting-edge",
"synergy", no em dashes, no keyword stuffing.

OUTPUT - valid JSON only (it plugs straight into the resume builder as tailoring.json):
{"company": "", "role": "<JD title>", "city": "",
 "company_profile": "<1 sentence: what the company does, for whom>",
 "title": "", "summary": "",
 "project": {"name": "", "bullets": ["", ""], "technologies": [""]},
 "cover_letter": {"greeting": "Dear Hiring Team,", "paragraphs": ["<intro>", "<motivation + company>", "<contribution>", "<Think Tree + close>"], "closing": "Sincerely,"},
 "jd_keywords": ["<8-15 of the JD's key skills/tools, JD wording>"],
 "experience_variant": "timeseries | base"}

Check before answering: the company name appears only in "company", "company_profile" and the cover
letter; the project has exactly 2 bullets; the summary adds nothing the resume doesn't show (the Think
Tree sentence is the one allowed addition); the summary's last sentence and the letter's 4th paragraph
both mention Think Tree; the letter has exactly 4 paragraphs, none over about 65 words, and paragraph 2
contains "fiancée", "Berlin" and the job's city.

BASE RESUME:
<<< paste base_resume/base_resume.txt >>>

JOB DESCRIPTION:
<<< paste JD >>>
```

To turn the output into PDFs with this project: save the JSON as
`applications/<date>/<Company>_<Title>_<City>/tailoring.json`, put the JD file in `jobs/jd_visa/<date>/`,
and run `.venv/bin/python build_resume.py --date <date>`.

---

## Prompt 4 - Judge (strict recruiter, use a different model / chat)

```
You are the hiring manager and HR recruiter at the job's company, screening applications for this role.
The ATS has already parsed the resume below (the base resume with the new title, summary and project
applied). Decide how well it matches THIS job, strictly and consistently. Score only what the resume
shows; give no credit for skills the JD needs but the resume lacks. You did not write this resume and
have no reason to be kind to it.

Rubric (points):
- tech_stack (30): the JD's languages, frameworks, cloud and tools appear in skills AND are used in the
  bullets of roles or projects.
- experience (25): roles and projects show the same kind of work at the level the JD asks for
  (seniority, ownership, production delivery).
- company_project (20): the newest project solves a believable problem of this company's domain with the
  JD's stack.
- ats_keywords (15): the JD's exact terms appear in context, not only in the skills list; standard
  section headings; job title alignment.
- credibility (10): concrete outcomes, consistent timeline, no filler or inflated-looking claims.

Anchors per criterion: full points = clearly and concretely shown, in context, as the JD asks; about half
= mentioned or adjacent but thin, only in the skills list, or at lower depth than asked; near zero =
missing or contradicted. A resume that would get an interview scores 80+; 90+ means nearly every
must-have of the JD is shown in the work, not just listed.

Be consistent: every gap you list must cost points in its criterion, and a criterion gets full points only
if you list no gap for it. Score first, then write the gaps, then check they agree.

Return valid JSON:
{"criteria": {"tech_stack": 0, "experience": 0, "company_project": 0, "ats_keywords": 0, "credibility": 0},
 "score": 0, "decision": "shortlist | maybe | reject",
 "strengths": ["up to 4"], "gaps": ["up to 5, most costly first"]}
score = the sum of the five criteria. Report it as it is.

TAILORED RESUME:
<<< paste >>>

JOB DESCRIPTION:
<<< paste JD >>>
```

---

## Appendix B - Time-series resume version

Apply to the Viavi Solutions (Senior Machine Learning Engineer) role when the JD is forecasting-heavy:
- Replace the bullet starting "Deployed a production-grade SLA breach prediction system" with:
  "Developed time-series forecasting of base-station call handover and SMS handover volumes using LSTM
  and XGBoost."
- Add: "Developed a forecasting feature for the AIOps monitoring product, forecasting univariate KPIs
  across the network."

---

## Appendix A - Base resume

In `base_resume/`: `base_resume.txt` (paste this text) and `Abhinav_kaushik_AI_ML.pdf` (the original).
