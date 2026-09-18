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
    groq_api_key: SecretStr
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"
    # Smaller jobs (summary merge, fact-check) use a separate model = separate Groq rate-limit bucket.
    groq_light_model: str = "openai/gpt-oss-20b"
    reasoning_effort: str = "low"  # low | medium | high (gpt-oss models)
    llm_temperature: float = 0.2
    llm_max_tokens: int = 6000
    # Groq tokens-per-minute limit per model (free tier: 8000). Each request's input plus
    # max output must fit, so max output is sized dynamically. Set 0 on paid tiers.
    llm_tpm_limit: int = 8000
    llm_timeout_seconds: float = 180.0
    llm_max_retries: int = 6

    # --- Files -------------------------------------------------------------
    base_resume_path: Path = PROJECT_ROOT / "base_resume.pdf"
    output_dir: Path = PROJECT_ROOT / "outputs"
    max_jd_bytes: int = 5 * 1024 * 1024
    min_jd_chars: int = 200

    # --- LaTeX -------------------------------------------------------------
    latex_engine: str = "auto"  # auto | tectonic | pdflatex
    latex_timeout_seconds: int = 180
    max_resume_pages: int = 2

    # --- Candidate (personal data lives in .env, never in code) ------------
    candidate_name: str
    candidate_email: str
    candidate_phone: str = ""
    candidate_location: str = ""
    candidate_linkedin_url: str = ""
    # Personal motivation woven into every cover letter (empty = not mentioned).
    relocation_motivation: str = ""

    # Project name substring -> URL, used to hyperlink projects (JSON in .env).
    project_links: dict[str, str] = Field(default_factory=dict)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
