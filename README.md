# ATS Resume Tailor

Paste a job description, get a tailored ATS-friendly resume and cover letter (PDF + LaTeX), named after the company.

## Run

```bash
./run.sh                      # web UI at http://127.0.0.1:8000
.venv/bin/python resume_tailor.py --jd path/to/jd.txt --city Brussels [--company "Flaconi"]   # CLI
```

Setup:

1. `brew install tectonic` (LaTeX engine).
2. `cp .env.example .env` and fill in your Groq key, name, email and other details. `.env` is git-ignored.
3. Put your base resume PDF in the project folder and set `BASE_RESUME_PATH` in `.env`. PDFs are git-ignored.

## How it works

**Base resume (constant) + LLM additions (per JD) = final resume.** The model never rewrites or removes anything from your resume.

1. Your base resume PDF is parsed into sections (`--show-base` shows the result). If a PDF line comes out with missing spaces, a warning is logged; add the correction to `BASE_RESUME_FIXES` in `.env` (JSON: `{"extracted text": "fixed text"}`).
2. **Plan** (`gpt-oss-120b`, medium reasoning): the model reads your resume and the JD, identifies the company and location, lists the 4-6 things the hire must deliver, maps each one to your closest real evidence, and designs **one project for the company's domain**. Plans are cached in `outputs/.cache/`, so re-running the same JD skips this call.
   **Write**: from the plan, the model adds 4-5 bullets to your existing roles, the new project (2 concise bullets), skills and summary phrases. Prompts are in `ats_tailor/prompts.py`. Your resume is sent first in every call so the provider can cache it.
3. Code inserts the additions and rejects bullets that restate an existing one, contain new numbers or scale words, move a tool to an employer where your resume doesn't show it, or name the target company. At most 2 new bullets are added per role.
4. **Coverage loop:** every JD keyword still missing from the resume is sent back to the model to be placed (up to `COVERAGE_ROUNDS`, default 2). The UI shows the final JD keyword coverage % and anything still missing.
5. Summary pointers are blended into your summary without rewriting its sentences (otherwise the base summary is kept).
6. Enter the job city (web UI field, or `--city`); it overrides the city detected from the JD. The cover letter opens with what you can do for the company, then proof, how you work, your goal, and your motivation. The motivation depends on the job's city: for Berlin, your fiancée already lives there; for any other city, your fiancée lives in Berlin and you plan to move to that city together (`PARTNER_TERM`, `PARTNER_CITY` in `.env`). It is fact-checked and patched, and a missing or wrong motivation line is fixed automatically.
7. Special symbols are removed and the resume is compiled to PDF. If it is over 2 pages (`MAX_RESUME_PAGES`), only *added* bullets are trimmed, starting with the ones whose JD keywords also appear elsewhere. Base content and the company project's bullets are never removed.

Output: `outputs/<Company>_<timestamp>/`.

Groq free tier allows 8k tokens/minute per model, so one generation takes about 1-2 minutes. On the Dev tier, set `LLM_TPM_LIMIT=0`.
