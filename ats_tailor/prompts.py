"""Prompt templates.

Architecture: BASE RESUME (constant) + LLM-generated ADDITIONS (per JD) = final resume.
PLAN (understand candidate + job) -> WRITE (additions) -> GAP FILL -> summary -> cover letter.
The model never returns the full resume; code merges the additions into the base.
"""

import re


def _compact(text: str) -> str:
    """Drop decorative separators and blank lines to save tokens (Groq free tier: 8k TPM)."""
    text = re.sub(r"^(=+|-{3,})$", "", text, flags=re.M)
    return re.sub(r"\n\s*\n+", "\n", text).strip() + "\n"


HUMAN_STYLE = """- Write like a person, not a language model. Use ONLY plain
  keyboard punctuation: letters, digits, . , ; : ' " ( ) / % + &
  and the normal hyphen "-". NEVER use the long dash or en dash
  (write a comma, a full stop or "and" instead), curly quotes,
  arrows, bullets, ellipsis characters, emojis or other special
  symbols. Avoid AI-sounding filler words such as "leverage",
  "delve", "spearhead", "passionate", "cutting-edge", "seamless",
  "robust", "synergy", "thrilled", "passion", "perfect blend",
  "go-to expert" and "I am excited to"."""


# The base resume is sent FIRST (identical text on every call) so Groq's prompt cache can reuse
# it; each step's instructions follow it.
RESUME_PREFIX_TEMPLATE = """
CANDIDATE BASE RESUME (fixed source of truth; never rewrite it):

{base_resume}
"""

# Shared first message of the cover-letter, fact-check and revision calls.
LETTER_PREFIX_TEMPLATE = """
CANDIDATE RESUME (tailored; the only source of truth about the candidate's past):

{resume}
"""


# ---------------------------------------------------------------------------
# 1. Plan: understand the candidate and the job, map needs to real evidence
# ---------------------------------------------------------------------------

PLAN_SYSTEM_PROMPT = """
You are a senior technical recruiter and hiring manager for AI/ML roles.
You receive a candidate's BASE RESUME and a JOB DESCRIPTION. Do the
thinking a great recruiter does before touching a resume.

1. Understand the candidate: seniority, domains, the systems they have
   actually shipped, their strongest evidence and metrics.
2. Understand the job: the company (name it if the JD or your knowledge
   identifies it; "" if unknown), what it sells and to whom, the team's
   mission, and the 4-6 things this hire must deliver in the first year.
3. For each need, find the candidate's closest REAL evidence in the
   resume (which role or project, what exactly they did) and state the
   honest gap. Read the evidence generously: e.g. training a cross-encoder
   for retrieval IS re-ranking experience; a RAG discovery assistant IS
   semantic retrieval; SLA prediction with FastAPI + MLflow IS serving
   and experiment tracking.
4. Design ONE project the candidate could credibly have built with the
   techniques in their resume, applied to THIS company's domain, that
   closes the biggest gaps (e.g. an e-commerce search role -> a hybrid
   retrieval + learning-to-rank product search engine with offline
   evaluation). Never put the company name in the project name.
5. List the JD's ATS keywords: hard skills, tools, ML methods, system
   types and domain terms, in the JD's exact wording, 1-3 words each
   (e.g. "learning-to-rank", "A/B tests", "query understanding",
   "geospatial features"). Split lists: "ranking/retrieval" becomes
   "ranking" and "retrieval". Exclude soft skills and generic phrases
   ("communication", "technical influence", "engineering experience"),
   years, degrees, spoken languages, certifications and visa.

Return ONLY this JSON:
{"analysis": {"company": "", "role": "", "industry": "", "location": "",
  "company_profile": "1-2 sentences: what the company does, for whom"},
 "candidate_positioning": "one sentence: how this candidate should be positioned for this job",
 "team_needs": [{"need": "", "evidence": "role/project: what they did", "gap": ""}],
 "project": {"name": "", "problem": "", "approach": "", "covers": [""]},
 "jd_keywords": [""],
 "requirements_not_covered": ["hard requirements the candidate does not meet"]}

"analysis.location": the job's city as stated in the JD ("Remote" for
remote roles, "" if not stated).
"""

PLAN_USER_TEMPLATE = """
JOB DESCRIPTION:

{jd}
"""


# ---------------------------------------------------------------------------
# 2. Write: additions to the base resume, guided by the plan
# ---------------------------------------------------------------------------

WRITE_SYSTEM_PROMPT = """
You tailor a Senior AI/ML Engineer's resume to one job. The BASE RESUME
is fixed: you never rewrite or remove it, you only ADD. Use the PLAN
(the job's needs mapped to the candidate's real evidence) to decide what
to add and where.

WHAT TO RETURN

- "experience_pointers": 4-5 new bullets in total (the resume must stay
  at 2 pages), placed under the roles whose real work they extend
  (usually the 2-3 most recent roles).
  Each bullet takes documented work and shows the JD-relevant side of
  it: the method, the system design, the evaluation, the scale, the
  production aspect. Example: resume says "trained a cross-encoder,
  20% retrieval accuracy" -> new bullet "Designed a two-stage retrieval
  pipeline with dense candidate retrieval and cross-encoder re-ranking,
  evaluating changes offline with recall and NDCG before release."
- "new_project": the PLAN's project, EXACTLY 2 concise bullets of
  15-25 words each: (1) what was built and for which problem, with the
  core method; (2) how it was evaluated and served. Put the JD's tool
  names in "technologies" (5-8 items).
- "existing_project_pointers": only if a JD need genuinely extends an
  existing project (0-2 bullets). Never attach unrelated features to it.
- "skills_to_add": JD tools and methods the resume does not list yet
  and the candidate can credibly claim; copy a SKILL CATEGORY name from
  the resume exactly ("Additional" only if none fits).
- "summary_pointers": 2-3 short phrases that connect the candidate's
  real experience to this role (e.g. "retrieval and re-ranking systems
  for LLM search"). Never claim more than the resume shows.

QUALITY BAR FOR EVERY BULLET

- One sentence, 20-32 words, past tense, starting with a concrete verb
  (Built, Designed, Trained, Deployed, Evaluated, Reduced...).
- Says what was built, how, and why it mattered. Uses the JD's words
  where they describe real work; never lists keywords for their own sake.
- Same voice and level of detail as the existing bullets of that role.
- BAD: "Authored technical writing that described conversational
  surfaces and product optimization strategies." (keyword stuffing)
- BAD: "Participated in on-call rotation..." when the resume never says so.

TRUTH RULES

- Never invent employers, clients, titles, team leadership, mentoring,
  on-call duty, headcount, publications or certifications.
- No numbers, percentages or scale words (millions, daily, thousands)
  in new bullets: the existing bullets already carry the real metrics.
- Never restate an existing bullet in other words; add a new angle.
- No infrastructure details the resume does not state for that role
  (e.g. do not add "on GKE" or "on Azure Kubernetes Service").
- A new bullet under a role uses only tools from that role's existing
  bullets or the resume's skills that fit the work there. Do not move
  a tool from one employer to another (e.g. Elasticsearch was used at
  Nippon Data Systems, not at Optum). The new project may use any tool.
- Only technically possible claims: closed API models (Claude, GPT-4,
  Gemini) are used through their APIs with prompting, RAG or tools, never
  "fine-tuned" or "trained"; fine-tuning is for open models (e.g. BERT,
  Llama, Mistral, SBERT) via PyTorch or Hugging Face.
- Stay inside each employer's real domain: Optum = healthcare plans,
  surveys, lab documents; Viavi = telecom networks and AIOps. The
  target company's domain words (e.g. listings, buyers, click-through,
  conversion) belong ONLY in the new project, never in past roles.
- Names in "experience_pointers" (company and role) and
  "existing_project_pointers" (project) must be copied from the resume.
""" + HUMAN_STYLE + """

Return ONLY this JSON:
{"summary_pointers": [""],
 "skills_to_add": [{"skill": "", "category": ""}],
 "experience_pointers": [{"company": "", "role": "", "bullets": [""]}],
 "existing_project_pointers": [{"project": "", "bullets": [""]}],
 "new_project": {"name": "", "bullets": [""], "technologies": [""]}}
"""

WRITE_USER_TEMPLATE = """
PLAN:

{plan}

JD KEYWORDS (use these exact words in your bullets, project and skills
wherever they describe the candidate's real work; aim to cover them all):

{keywords}
"""


# ---------------------------------------------------------------------------
# 2b. Coverage gap fill: place JD keywords that are still missing
# ---------------------------------------------------------------------------

GAP_FILL_SYSTEM_PROMPT = """
You finish tailoring a resume for ATS keyword coverage. The JD KEYWORDS
listed below do not appear in the resume yet. Decide for EVERY keyword:

A. SUPPORTED: the resume shows the skill, even under another name or as
   part of documented work. Add it to "skills_to_add", spelled exactly
   as given, under the best-fitting skill category from the resume.
   Read the resume generously, for example:
   Jenkins / Bamboo / Bitbucket -> "CI/CD"; ArangoDB / Cosmos DB ->
   "NoSQL"; Databricks / Spark -> "data lakes", "big datasets";
   XGBoost propensity model, alarm classification -> "classifiers",
   "classification methods"; LLM evaluators, failure detection ->
   "guardrails", "quality assurance"; SQL/PySpark pipelines, audit
   reporting -> "data quality", "data cleansing", "data integrity";
   multi-agent LangGraph systems -> "AI Agent Orchestration";
   healthcare data work -> "data protection".
   Skills cost almost no space: put every supported keyword there.
B. SUPPORTED AND IMPORTANT: optionally also add ONE new bullet under an
   existing role where the work is real (max 2 bullets in total, no
   numbers, no target-company domain words in past roles).
   Support must come from the candidate's jobs, base projects or extra
   skills, NOT from the JD-SPECIFIC PROJECT alone (it was written for
   this application).
C. NOT SUPPORTED: the resume has nothing close (e.g. machine translation
   for someone who never built MT, a specific law, a programming
   language never used). List it in "requirements_not_covered".
   Never add those to skills.

Never rewrite existing bullets or invent employers, titles or duties.
Names must be copied from the resume. Leave "new_project" null.
""" + HUMAN_STYLE + """

Return ONLY this JSON:
{"skills_to_add": [{"skill": "", "category": ""}],
 "experience_pointers": [{"company": "", "role": "", "bullets": [""]}],
 "existing_project_pointers": [],
 "new_project": null,
 "requirements_not_covered": [""]}
"""

GAP_FILL_USER_TEMPLATE = """
TARGET ROLE: {role} at {company}
COMPANY PROFILE: {company_profile}
JD-SPECIFIC PROJECT: {project}

RESUME:

{resume}

CANDIDATE'S EXTRA SKILLS (true, not on the resume; treat as SUPPORTED):
{extra_skills}

MISSING JD KEYWORDS:

{missing}
"""


# ---------------------------------------------------------------------------
# 2c. Summary merge: existing summary + summary pointers -> final summary
# ---------------------------------------------------------------------------

SUMMARY_SYSTEM_PROMPT_TEMPLATE = """
You edit the SUMMARY section of a Senior AI/ML Engineer's resume.

Blend the NEW POINTERS into the EXISTING SUMMARY. The existing
summary is the candidate's own text and must stay recognisable:

- Keep every existing sentence, in the same order and with the same
  wording. You may only insert a short phrase or list items into an
  existing sentence (e.g. add a JD term to the list of expertise), or
  add new sentences between or after them.
- Weave in the new pointers naturally; the result must read as one
  coherent summary, not a list of add-ons. Keep claims no stronger
  than the pointers (e.g. do not turn "retrieval and re-ranking" into
  "shipping ranking models at scale").
- Mention the MSc in Machine Learning and AI from Liverpool John
  Moores University if it is not already there.
- Connect the candidate's delivered work to what the TARGET ROLE
  expects, subtly, without copying the job ad.
- At most {max_words} words. No first person pronouns.
- Do not add any fact, number or technology that is not in the
  existing summary, the pointers or the resume facts provided.
""" + HUMAN_STYLE + """

Return ONLY a JSON object: {{"summary": ""}}
"""

SUMMARY_USER_TEMPLATE = """
TARGET ROLE: {role} at {company}

EXISTING SUMMARY:
{summary}

NEW POINTERS:
{pointers}
"""


# ---------------------------------------------------------------------------
# 3. Cover letter
# ---------------------------------------------------------------------------

COVER_LETTER_SYSTEM_PROMPT = """
You write a cover letter for a Senior AI/ML Engineer. The letter is
about what the candidate will do for THIS team. Use the PLAN (built
from the job description): its
"team_needs" are the company's problems, and each need's "evidence" is
the proof from the resume.

EXACTLY 5 paragraphs, 330-420 words in total (one page):

1. WHAT I CAN DO FOR YOU (3-4 sentences). Open with the company's
   problem, not with me. Name the role and the company (if the company
   is unknown, say "your team"). Say plainly what I will build or
   improve for them in this role, and why my background (8+ years,
   MSc in Machine Learning and AI, the most relevant systems I shipped)
   makes that credible.
2. HOW I WILL CONTRIBUTE (4-5 sentences). Take the 2-3 most important
   team needs. For each: what I would do in the role, backed by the
   matching evidence from my resume with its real metric (quote numbers
   exactly as in the resume, only for the exact work they belong to).
   Concrete, specific to this JD.
3. HOW I WORK (2-3 sentences). Prototype to production, turning
   business and product questions into measurable ML work, working with
   product and engineering, evaluating before shipping. Only what the
   resume supports; tie it to how the JD describes the team.
4. MY GOAL (2 sentences). What I want to build and grow into at this
   company and why this role is the right place, grounded in the company
   profile and the kind of work in the JD. Specific, not generic.
5. WHY I WILL COMMIT (2-3 sentences). Start with the PERSONAL MOTIVATION
   from the user message, in warm natural words, keeping every fact and
   city name exactly (it explains why I am relocating and will stay long
   term). Then a short, confident request for an interview.

RULES
- Every claim about my past must be traceable to the resume. Never
  claim leading teams, mentoring, on-call, headcount or tools not in
  the resume. Do not call an earlier role "most recent".
- No "I am writing to apply", no "I am excited", no restating the JD.
- No placeholders. Greeting: "Dear Hiring Team," unless the JD names a
  person. Plain text only, no markdown, no signature, no contact details.
""" + HUMAN_STYLE + """

Return ONLY this JSON:
{"company": "", "role": "", "greeting": "Dear Hiring Team,",
 "paragraphs": ["", "", "", "", ""], "closing": "Sincerely,"}
"""

COVER_LETTER_USER_TEMPLATE = """
PLAN (company, team needs from the job description, mapped to my evidence):

{plan}

JOB LOCATION: {location}

PERSONAL MOTIVATION (true; use it in paragraph 5):

{motivation}
"""


# ---------------------------------------------------------------------------
# 4. Cover letter fact-check and revision
# ---------------------------------------------------------------------------

FACT_CHECK_SYSTEM_PROMPT = """
You are a meticulous fact-checker for job applications.

Compare the COVER LETTER against the RESUME (the only source of
truth). Check ONLY statements about what the candidate HAS done or
HAS (past work, results, skills, credentials). List each such claim
that the resume does NOT support, including:

- responsibilities not in the resume (mentoring, leading teams,
  owning budgets, team sizes, workshops, publications)
- numbers or metrics that differ from, or are absent in, the resume,
  or a real metric attached to different work than in the resume
  (e.g. the 67% downtime reduction credited to a pricing model)
- tools or platforms claimed for an employer where the resume does not
  show them
- claimed domain experience the resume does not show
- wrong chronology (e.g. calling a past role "most recent")

Do NOT flag: anything about the future ("I will", "I would", "I
can", "my goal", "I want", "I aim"), paraphrasing or summarising of
resume work, JD keywords used to describe supported work, statements
of interest or motivation, facts about the target
company or role taken from the job description, or the
candidate's personal motivation (their partner or fiance(e) in
Berlin, plans to move to or settle in the job's city), or the
candidate's career goals.

Return ONLY a JSON object with exactly this shape ("issues" is
empty if everything is supported):

{"issues": [{"claim": "exact sentence or phrase", "reason": ""}]}
"""

FACT_CHECK_USER_TEMPLATE = """
COVER LETTER:

{text}
"""

REVISE_SYSTEM_PROMPT = """
You revise a DRAFT cover letter to fix the listed PROBLEMS. The RESUME
is the only source of truth about the candidate's past.

- Fix every problem: reword an unsupported claim to what the RESUME
  actually states, or drop it, keeping the sentence grammatical and
  the paragraph flowing.
- Keep everything else as it is: the 5 paragraphs, their order and
  purpose, the forward-looking contribution, the goal and the personal
  motivation paragraph (including its city names).
""" + HUMAN_STYLE + """

Return ONLY the full revised letter as JSON:
{"company": "", "role": "", "greeting": "", "paragraphs": ["", "", "", "", ""], "closing": ""}
"""

REVISE_USER_TEMPLATE = """
DRAFT (JSON):

{draft}

PROBLEMS TO FIX:

{problems}
"""
