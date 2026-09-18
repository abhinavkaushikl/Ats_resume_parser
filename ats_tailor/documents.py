"""Text extraction for the base resume and uploaded job descriptions."""

import io
import re
from functools import lru_cache
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_JD_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class DocumentError(ValueError):
    pass


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def pdf_to_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return _normalize("\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception as exc:  # pypdf raises many different error types
        raise DocumentError(f"Could not read PDF: {exc}") from exc


def docx_to_text(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError(f"Could not read DOCX: {exc}") from exc
    return _normalize("\n".join(p.text for p in doc.paragraphs))


def extract_jd_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_JD_EXTENSIONS:
        raise DocumentError(
            f"Unsupported file type '{ext}'. Use one of: {', '.join(sorted(SUPPORTED_JD_EXTENSIONS))}"
        )
    if ext == ".pdf":
        return pdf_to_text(data)
    if ext == ".docx":
        return docx_to_text(data)
    return _normalize(data.decode("utf-8", errors="replace"))


@lru_cache(maxsize=4)
def _load_base_resume(path: Path, mtime: float) -> str:
    return pdf_to_text(path.read_bytes())


def load_base_resume(path: Path) -> str:
    """Base resume text, cached until the PDF changes on disk."""
    if not path.exists():
        raise DocumentError(f"Base resume not found: {path}")
    text = _load_base_resume(path, path.stat().st_mtime)
    if not text:
        raise DocumentError(f"No text could be extracted from {path}")
    return text
