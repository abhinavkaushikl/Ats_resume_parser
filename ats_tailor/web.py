"""FastAPI app: upload a JD, get a tailored resume + cover letter."""

import logging
import threading
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import APIError, AuthenticationError, RateLimitError

from . import __version__
from .config import get_settings
from .base_resume import load_base
from .documents import DocumentError, extract_jd_text
from .llm import LLMError
from .pipeline import TailoringPipeline, job_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("ats_tailor")

STATIC_DIR = Path(__file__).parent / "static"
MEDIA_TYPES = {".pdf": "application/pdf", ".tex": "application/x-tex"}

settings = get_settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
pipeline = TailoringPipeline(settings)
# Groq rate limits are per key; cap concurrent generations to avoid 429 storms.
_generation_lock = threading.Semaphore(2)

app = FastAPI(title="ATS Resume Tailor", version=__version__)


@app.get("/api/health")
def health() -> dict:
    load_base(settings.base_resume_path, settings.base_resume_fixes)  # fails fast if the base PDF cannot be parsed
    return {"status": "ok", "model": settings.groq_model, "version": __version__}


@app.post("/api/generate")
def generate(
    jd_file: UploadFile | None = File(default=None),
    jd_text: str = Form(default=""),
    company: str = Form(default="", max_length=120),
    city: str = Form(default="", max_length=80),
) -> dict:
    # Sync endpoint: FastAPI runs it in a worker thread, so the event loop stays free.
    if jd_file and jd_file.filename:
        data = jd_file.file.read(settings.max_jd_bytes + 1)
        if len(data) > settings.max_jd_bytes:
            raise HTTPException(413, "File too large (max 5 MB).")
        try:
            text = extract_jd_text(jd_file.filename, data)
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        text = jd_text

    if not text.strip():
        raise HTTPException(400, "Upload a JD file or paste the job description.")

    with _generation_lock:
        try:
            result = pipeline.run(text, company=company, city=city)
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        except AuthenticationError as exc:
            log.error("Groq authentication failed: %s", exc)
            raise HTTPException(502, "Groq rejected the API key. Check GROQ_API_KEY in .env.") from exc
        except RateLimitError as exc:
            raise HTTPException(429, "Groq rate limit reached. Wait a minute and retry.") from exc
        except (APIError, LLMError) as exc:
            log.exception("LLM failure")
            raise HTTPException(502, f"Language model error: {exc}") from exc

    payload = asdict(result)
    payload["downloads"] = {
        kind: f"/api/jobs/{result.job_id}/{name}" for kind, name in result.files.items()
    }
    return payload


@app.get("/api/jobs/{job_id}/{filename}")
def download(job_id: str, filename: str, inline: bool = False) -> FileResponse:
    try:
        directory = job_dir(settings, job_id).resolve()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    path = (directory / filename).resolve()
    if path.parent != directory or path.suffix not in MEDIA_TYPES or not path.is_file():
        raise HTTPException(404, "File not found.")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[path.suffix],
        filename=path.name,
        content_disposition_type="inline" if inline else "attachment",
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
