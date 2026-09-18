"""End-to-end orchestration.

    BASE RESUME (constant, parsed from PDF)
  + ADDITIONS   (LLM, per JD: only new skills / bullets / projects / pointers)
  = FINAL RESUME -> merged summary -> cover letter -> LaTeX -> PDF
"""

import json
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .base_resume import load_base
from .config import Settings
from .documents import DocumentError
from .latex import LatexError, compile_pdf, pdf_page_count, render_cover_letter, render_resume
from .llm import LLMClient
from .merge import merge
from .prompts import (
    ADDITIONS_SYSTEM_PROMPT,
    ADDITIONS_USER_TEMPLATE,
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_TEMPLATE,
    FACT_CHECK_SYSTEM_PROMPT,
    FACT_CHECK_USER_TEMPLATE,
    PATCH_SYSTEM_PROMPT,
    PATCH_USER_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_TEMPLATE,
)
from .schemas import CoverLetter, FactCheck, MergedSummary, Patch, Project, Resume, ResumeAdditions
from .text import plain_text, unsupported_numbers

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)

MAX_REPAIR_ROUNDS = 2
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
# Base-resume projects that may be dropped when the resume is over the page limit.
DROPPABLE_PROJECTS = ("Restaurant Feedback",)


@dataclass
class GenerationResult:
    job_id: str
    company: str
    role: str
    industry: str
    files: dict[str, str]  # kind -> filename inside the job directory
    added: dict[str, int] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    not_covered: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resume_pages: int | None = None


def _slug(text: str, limit: int = 40) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:limit] or "Company"


def job_dir(settings: Settings, job_id: str) -> Path:
    if not JOB_ID_RE.match(job_id):
        raise ValueError("Invalid job id")
    return settings.output_dir / job_id


def _clean(doc: M) -> M:
    """Apply `plain_text` to every string field of a model."""

    def walk(node):
        if isinstance(node, str):
            return plain_text(node)
        if isinstance(node, list):
            return [walk(n) for n in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return type(doc).model_validate(walk(doc.model_dump()))


def _apply_patch(letter: CoverLetter, patch: Patch) -> CoverLetter:
    edits = [r for r in patch.replacements if r.find and r.find != r.replace]
    if not edits:
        return letter
    paragraphs = []
    for p in letter.paragraphs:
        for r in edits:
            p = p.replace(r.find, r.replace)
        if p := re.sub(r"\s{2,}", " ", p).strip():
            paragraphs.append(p)
    try:
        return CoverLetter(**{**letter.model_dump(), "paragraphs": paragraphs})
    except ValidationError as exc:
        log.warning("Patch produced an invalid letter; keeping previous version: %s", exc)
        return letter


def _trim_once(resume: Resume, base: Resume) -> str | None:
    """Remove the lowest-value content to shorten the resume. Returns what was removed."""
    for name in DROPPABLE_PROJECTS:
        for p in resume.projects:
            if name.lower() in p.name.lower() and not p.added:
                resume.projects.remove(p)
                return f"project '{p.name}'"
    if len(resume.additional_info) > len(base.additional_info):
        return f"additional info '{resume.additional_info.pop()}'"
    if resume.education_notes:
        return f"education note '{resume.education_notes.pop()}'"
    # Added bullets: take from whichever entry has the most additions (older roles first on ties).
    entries = [e for e in (*reversed(resume.experience), *resume.projects) if e.added]
    if not entries:
        return None
    target = max(entries, key=lambda e: e.added)
    target.added -= 1
    bullet = target.bullets.pop()
    if isinstance(target, Project) and target.is_new and not target.bullets:
        resume.projects.remove(target)
    return f"added bullet '{bullet}'"


class TailoringPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    # ------------------------------------------------------------------ LLM steps

    def _additions(self, base: Resume, jd: str) -> ResumeAdditions:
        return self.llm.structured(
            ADDITIONS_SYSTEM_PROMPT,
            ADDITIONS_USER_TEMPLATE.format(base_resume=base.as_text(), jd=jd),
            ResumeAdditions,
        )

    def _summary(self, resume: Resume, adds: ResumeAdditions) -> str:
        pointers = [plain_text(p) for p in adds.summary_pointers if p.strip()]
        if not pointers:
            return resume.summary
        merged = self.llm.structured(
            SUMMARY_SYSTEM_PROMPT,
            SUMMARY_USER_TEMPLATE.format(
                role=adds.analysis.role,
                company=adds.analysis.company,
                summary=resume.summary,
                pointers="\n".join(f"- {p}" for p in pointers),
            ),
            MergedSummary,
            model=self.settings.groq_light_model,
        )
        summary = plain_text(merged.summary)
        if bad := unsupported_numbers(summary, resume.as_text()):
            log.warning("Merged summary has unknown numbers %s; keeping base summary", bad)
            return resume.summary
        return summary

    def _letter_problems(self, letter: CoverLetter, resume_text: str, jd: str) -> list[str]:
        text = "\n\n".join(letter.paragraphs)
        errors = [
            f"Number '{n}' does not appear in the resume or JD; remove it or quote the resume exactly."
            for n in unsupported_numbers(text, f"{resume_text}\n{jd}")
        ]
        check = self.llm.structured(
            FACT_CHECK_SYSTEM_PROMPT,
            FACT_CHECK_USER_TEMPLATE.format(resume=resume_text, text=text),
            FactCheck,
            model=self.settings.groq_light_model,
        )
        return errors + [f'Unsupported claim: "{i.claim}" ({i.reason})' for i in check.issues]

    def _cover_letter(self, resume: Resume, jd: str) -> tuple[CoverLetter, list[str]]:
        resume_text = resume.as_text()
        letter = _clean(self.llm.structured(
            COVER_LETTER_SYSTEM_PROMPT,
            COVER_LETTER_USER_TEMPLATE.format(
                resume=resume_text, jd=jd, motivation=self.settings.relocation_motivation
                or "None provided. Do not mention relocation or personal reasons."
            ),
            CoverLetter,
        ))
        for round_no in range(1, MAX_REPAIR_ROUNDS + 1):
            errors = self._letter_problems(letter, resume_text, jd)
            if not errors:
                return letter, []
            log.warning("Cover letter round %d: %d problem(s): %s", round_no, len(errors), errors)
            draft = "\n".join(f"[paragraph {i}] {p}" for i, p in enumerate(letter.paragraphs, 1))
            patch = self.llm.structured(
                PATCH_SYSTEM_PROMPT,
                PATCH_USER_TEMPLATE.format(
                    resume=resume_text, draft=draft, problems="\n".join(f"- {e}" for e in errors)
                ),
                Patch,
            )
            letter = _clean(_apply_patch(letter, patch))
        return letter, [f"Cover letter: {e}" for e in self._letter_problems(letter, resume_text, jd)]

    # ------------------------------------------------------------------ output

    def _fit_pages(self, resume: Resume, base: Resume, tex_path: Path) -> tuple[Resume, int, list[str]]:
        """Compile; while over the page limit, trim the lowest-value content."""
        trimmed: list[str] = []
        while True:
            tex_path.write_text(render_resume(resume, self.settings), encoding="utf-8")
            pages = pdf_page_count(compile_pdf(tex_path, self.settings))
            if pages <= self.settings.max_resume_pages:
                break
            # Trim two items per compile to keep the loop short.
            removed = [r for r in (_trim_once(resume, base), _trim_once(resume, base)) if r]
            if not removed:
                break
            trimmed += removed
            log.info("Resume is %d pages; trimmed %s", pages, removed)
        return resume, pages, trimmed

    def run(self, jd_text: str, company: str | None = None) -> GenerationResult:
        """Generate both documents. `company` overrides the name detected from the JD."""
        jd_text = jd_text.strip()
        company = (company or "").strip()
        if len(jd_text) < self.settings.min_jd_chars:
            raise DocumentError(
                f"The job description is too short ({len(jd_text)} characters). "
                "Paste or upload the full JD."
            )

        base = load_base(self.settings.base_resume_path)
        log.info("JD %d chars", len(jd_text))

        adds = _clean(self._additions(base, jd_text))
        if company:
            adds.analysis.company = company
        company = adds.analysis.company or "Company"
        resume, report = merge(base, adds)

        # Summary (light model) and cover letter (main model) use separate rate-limit buckets.
        with ThreadPoolExecutor(max_workers=2) as pool:
            summary_future = pool.submit(self._summary, resume, adds)
            letter_future = pool.submit(self._cover_letter, resume, jd_text)
            resume.summary = summary_future.result()
            letter, warnings = letter_future.result()
        letter.company = company
        warnings = report.dropped + warnings

        job_id = f"{_slug(company)}_{datetime.now():%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:4]}"
        out = job_dir(self.settings, job_id)
        out.mkdir(parents=True, exist_ok=True)

        stem = f"{_slug(self.settings.candidate_name)}_{_slug(company)}"
        resume_tex = out / f"{stem}_Resume.tex"
        letter_tex = out / f"{stem}_Cover_Letter.tex"
        (out / "job_description.txt").write_text(jd_text, encoding="utf-8")

        resume_tex.write_text(render_resume(resume, self.settings), encoding="utf-8")
        letter_tex.write_text(render_cover_letter(letter, resume.headline, self.settings), encoding="utf-8")
        files = {"resume_tex": resume_tex.name, "cover_letter_tex": letter_tex.name}
        pages = None

        try:
            resume, pages, trimmed = self._fit_pages(resume, base, resume_tex)
            if trimmed:
                warnings.append(
                    f"To fit {self.settings.max_resume_pages} pages, removed {len(trimmed)} item(s): "
                    + "; ".join(trimmed)
                )
            if pages > self.settings.max_resume_pages:
                warnings.append(f"Resume is {pages} pages (target {self.settings.max_resume_pages}).")
            files["resume_pdf"] = resume_tex.with_suffix(".pdf").name
            compile_pdf(letter_tex, self.settings)
            files["cover_letter_pdf"] = letter_tex.with_suffix(".pdf").name
        except LatexError as exc:
            log.error("%s\n%s", exc, exc.log_tail)
            warnings.append(f"PDF compilation failed: {exc}. The .tex files are available.")

        result = GenerationResult(
            job_id=job_id,
            company=company,
            role=adds.analysis.role,
            industry=adds.analysis.industry,
            files=files,
            added=report.added,
            keywords=adds.keywords_covered,
            not_covered=adds.requirements_not_covered,
            warnings=warnings,
            resume_pages=pages,
        )
        (out / "report.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        log.info("Job %s complete: %s", job_id, files)
        return result
