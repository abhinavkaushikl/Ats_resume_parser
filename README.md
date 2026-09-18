# ATS Resume Tailor

Paste a job description, get a tailored ATS-friendly resume and cover letter (PDF + LaTeX), named after the company.

## Run

```bash
./run.sh                      # web UI at http://127.0.0.1:8000
.venv/bin/python resume_tailor.py --jd path/to/jd.txt [--company "Flaconi"]   # CLI
```

Setup:

1. `brew install tectonic` (LaTeX engine).
2. `cp .env.example .env` and fill in your Groq key, name, email and other details. `.env` is git-ignored.
3. Put your base resume PDF in the project folder and set `BASE_RESUME_PATH` in `.env`. PDFs are git-ignored.

## How it works

**Base resume (constant) + LLM additions (per JD) = final resume.** The model never rewrites your resume.

1. Your base resume PDF is parsed into sections (`--show-base` shows the result).
2. The model (Groq `openai/gpt-oss-120b`) compares it with the JD and returns only additions: missing skills, new bullets for existing roles and projects, one new project if justified, summary pointers, education and additional info. The prompt is in `ats_tailor/prompts.py`.
3. Code inserts the additions. Duplicates are skipped, names are matched to your real roles and projects, and bullets with numbers that are not in your resume are dropped.
4. The summary pointers are merged into your summary (`gpt-oss-20b`). The cover letter is written from the final resume, then fact-checked and patched.
5. Long dashes, curly quotes and other special symbols are removed. The resume is compiled to PDF. If it is over 2 pages (`MAX_RESUME_PAGES`), the lowest-value additions are trimmed and listed in the UI.

Output: `outputs/<Company>_<timestamp>/`.

Groq free tier allows 8k tokens/minute per model, so one generation takes about 1-2 minutes. On the Dev tier, set `LLM_TPM_LIMIT=0`.
