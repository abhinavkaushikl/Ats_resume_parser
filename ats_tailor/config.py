"""Application settings, loaded from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------------
    groq_api_key: SecretStr = SecretStr("")
    # Extra keys (comma-separated), used when a key hits its rate limit, e.g. its daily token cap.
    groq_api_keys: SecretStr = SecretStr("")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"
    # The summary merge uses a separate model = separate Groq rate-limit bucket.
    groq_light_model: str = "openai/gpt-oss-20b"
    reasoning_effort: str = "low"  # low | medium | high (gpt-oss models), for checks and small edits
    # Planning, writing the additions and the cover letter need real reasoning.
    writing_reasoning_effort: str = "medium"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 6000
    # Groq tokens-per-minute limit per model (free tier: 8000). Each request's input plus
    # max output must fit, so max output is sized dynamically. Set 0 on paid tiers.
    llm_tpm_limit: int = 8000
    llm_timeout_seconds: float = 180.0
    llm_max_retries: int = 6
    # Without a fallback model: how long to wait for a capped Groq key to reset instead of failing.
    llm_max_wait_minutes: int = 240
    # Fallback model (OpenAI, or any OpenAI-compatible API). Used when Groq is unavailable or not configured;
    # it is enabled by setting FALLBACK_LLM_API_KEY.
    fallback_llm_base_url: str = "https://api.openai.com/v1"
    fallback_llm_model: str = ""
    fallback_llm_api_key: SecretStr = SecretStr("")
    fallback_llm_timeout_seconds: float = 300.0

    # --- Files -------------------------------------------------------------
    base_resume_path: Path = PROJECT_ROOT / "base_resume.pdf"
    output_dir: Path = PROJECT_ROOT / "outputs"
    max_jd_bytes: int = 5 * 1024 * 1024
    min_jd_chars: int = 200

    # --- LaTeX -------------------------------------------------------------
    latex_engine: str = "auto"  # auto | tectonic | pdflatex
    latex_timeout_seconds: int = 180
    max_resume_pages: int = 2

    # --- Tailoring mode ----------------------------------------------------
    # subtle: only the title (the JD's job title), the summary (tweaked toward the JD) and ONE new project
    #         fitting the company's profile change. Experience, skills and the other projects - Think Tree
    #         above all - stay exactly as in the base resume. No company name anywhere. The judge scores it
    #         once (no revision loop). About 5 LLM calls per job.
    # full:   rewrites across the resume (headline, summary, experience bullets, skills, project) and runs
    #         the judge / revision loop. About 6-11 LLM calls per job.
    tailor_mode: str = "subtle"

    # --- JD coverage -------------------------------------------------------
    # Extra LLM rounds that place JD keywords still missing from the resume.
    coverage_rounds: int = 1

    # --- Reflection (HR / ATS judge) ----------------------------------------
    # The judge scores the tailored resume out of 100; below the pass mark it is revised and re-judged.
    judge_enabled: bool = True
    judge_pass_score: int = 95
    judge_max_revisions: int = 3
    # Stop early after this many revisions in a row that did not raise the score.
    judge_patience: int = 2

    # --- Candidate (personal data lives in .env, never in code) ------------
    candidate_name: str
    candidate_email: str
    candidate_phone: str = ""
    candidate_location: str = ""
    candidate_linkedin_url: str = ""
    # Cover-letter motivation: the partner lives in `partner_city`. For a job there the letter
    # says so; for any other city it says the partner is in `partner_city` and you plan to move
    # to the job's city together.
    partner_term: str = "fiancée"
    partner_city: str = "Berlin"
    # Optional extra personal motivation added to the cover letter facts.
    relocation_motivation: str = ""

    # Skills you really have that are not on the base resume PDF (comma-separated). They are added
    # to a tailored resume only when the JD asks for them; the base resume is not changed.
    extra_skills: str = ""

    # Exact extracted base-resume text -> correction, for PDF extraction glitches (JSON in .env).
    base_resume_fixes: dict[str, str] = Field(default_factory=dict)

    # Project name substring -> URL, used to hyperlink projects (JSON in .env).
    project_links: dict[str, str] = Field(default_factory=dict)


    def all_groq_keys(self) -> list[str]:
        keys = [self.groq_api_key.get_secret_value()]
        keys += [k.strip() for k in self.groq_api_keys.get_secret_value().split(",")]
        return list(dict.fromkeys(k for k in keys if k))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
