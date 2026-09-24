"""LaTeX rendering (Jinja2 templates with safe escaping) and PDF compilation."""

import logging
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pypdf import PdfReader

from .config import Settings
from .schemas import CoverLetter, Resume

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"

_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
    "→": r"$\rightarrow$",
    "•": r"\textbullet{}",
    " ": " ",
}
_LATEX_RE = re.compile("|".join(re.escape(k) for k in _LATEX_SPECIALS))


class LatexError(RuntimeError):
    def __init__(self, message: str, log_tail: str = ""):
        super().__init__(message)
        self.log_tail = log_tail


def tex_escape(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return _LATEX_RE.sub(lambda m: _LATEX_SPECIALS[m.group()], text)


def tex_url(value: str) -> str:
    return re.sub(r"([%#])", r"\\\1", value)


_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    block_start_string="((*",
    block_end_string="*))",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="((#",
    comment_end_string="#))",
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    undefined=StrictUndefined,
)
_env.filters["tex"] = tex_escape
_env.filters["url"] = tex_url


def _profile(settings: Settings) -> dict:
    email = settings.candidate_email
    contact = [tex_escape(v) for v in (settings.candidate_location, settings.candidate_phone) if v]
    contact.append(rf"\href{{mailto:{tex_url(email)}}}{{{tex_escape(email)}}}")
    if settings.candidate_linkedin_url:
        contact.append(rf"\href{{{tex_url(settings.candidate_linkedin_url)}}}{{LinkedIn}}")
    return {"name": settings.candidate_name, "contact": r" \textbar{} ".join(contact)}


def _project_link(name: str, settings: Settings) -> str:
    for key, url in settings.project_links.items():
        if key.lower() in name.lower():
            return url
    return ""


def render_resume(resume: Resume, settings: Settings) -> str:
    projects = [
        {"p": p, "url": _project_link(p.name, settings)} for p in resume.projects
    ]
    return _env.get_template("resume.tex.j2").render(
        profile=_profile(settings), r=resume, projects=projects
    )


def render_cover_letter(letter: CoverLetter, headline: str, settings: Settings) -> str:
    return _env.get_template("cover_letter.tex.j2").render(
        profile=_profile(settings),
        headline=headline,
        letter=letter,
        today=date.today().strftime("%B %d, %Y").replace(" 0", " "),
    )


# Install locations often missing from PATH (e.g. when the server starts from an IDE or launcher).
_EXTRA_BIN_DIRS = os.pathsep.join(
    str(Path(d).expanduser()) for d in ("~/.local/bin", "~/.cargo/bin", "/opt/homebrew/bin", "/Library/TeX/texbin")
)


def _engine_command(settings: Settings, tex_name: str) -> list[str]:
    engines = {
        "tectonic": ["tectonic", "--keep-logs", "--chatter", "minimal", tex_name],
        "pdflatex": ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_name],
    }
    order = [settings.latex_engine] if settings.latex_engine != "auto" else ["tectonic", "pdflatex"]
    for name in order:
        if name in engines and (path := shutil.which(name) or shutil.which(name, path=_EXTRA_BIN_DIRS)):
            return [path, *engines[name][1:]]
    raise LatexError(
        "No LaTeX engine found. Install one with `brew install tectonic` "
        "(or MacTeX for pdflatex). The .tex file was still generated."
    )


def compile_pdf(tex_path: Path, settings: Settings) -> Path:
    cmd = _engine_command(settings, tex_path.name)
    log.info("Compiling %s with %s", tex_path.name, cmd[0])
    try:
        proc = subprocess.run(
            cmd,
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            timeout=settings.latex_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise LatexError(f"LaTeX compilation timed out after {exc.timeout}s") from exc

    pdf_path = tex_path.with_suffix(".pdf")
    if proc.returncode != 0 or not pdf_path.exists():
        tail = (proc.stdout + proc.stderr)[-3000:]
        raise LatexError(f"LaTeX compilation failed for {tex_path.name}", tail)

    for ext in (".aux", ".log", ".out"):
        tex_path.with_suffix(ext).unlink(missing_ok=True)
    return pdf_path


def pdf_page_count(pdf_path: Path) -> int:
    return len(PdfReader(pdf_path).pages)
