"""End-to-end orchestration.

    BASE RESUME (constant, parsed from PDF)
  + PLAN        (LLM: company, team needs mapped to the candidate's real evidence, project idea)
  + ADDITIONS   (LLM, from the plan: new skills / bullets / pointers + one company-specific project)
  + GAP FILL    (LLM, until every JD keyword appears in the resume)
  = FINAL RESUME -> merged summary -> cover letter -> LaTeX -> PDF
"""

import hashlib
import json
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .base_resume import load_base
from .config import Settings
from .documents import DocumentError
from .latex import LatexError, compile_pdf, pdf_page_count, render_cover_letter, render_resume
from .llm import LLMClient, LLMError
from .merge import MergeReport, merge
from .reflection import ResumeReflector, _aligned_headline
from .prompts import (
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_TEMPLATE,
    GAP_FILL_SYSTEM_PROMPT,
    GAP_FILL_USER_TEMPLATE,
    LETTER_PREFIX_TEMPLATE,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_TEMPLATE,
    RESUME_PREFIX_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT_TEMPLATE,
    SUMMARY_USER_TEMPLATE,
    WRITE_SYSTEM_PROMPT,
    WRITE_USER_TEMPLATE,
)
from .schemas import CoverLetter, JobPlan, MergedSummary, Project, Resume, ResumeAdditions
from .text import has_keyword, key, missing_keywords, norm, plain_text, unsupported_numbers

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)

JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
# How many words the blended summary may add on top of the base summary.
SUMMARY_EXTRA_WORDS = 45
# A base summary sentence counts as kept if the merged summary has one at least this similar.
SUMMARY_KEEP_RATIO = 0.75
# The JD-specific project keeps at least this many bullets when trimming for page length.
MIN_JD_PROJECT_BULLETS = 2
# HR judge score the rubric anchors as "would get an interview"; below it the UI warns.
INTERVIEW_SCORE = 80


@dataclass
class GenerationResult:
    job_id: str
    company: str
    role: str
    industry: str
    files: dict[str, str]  # kind -> filename inside the job directory
    added: dict[str, int] = field(default_factory=dict)
    location: str = ""
    keywords: list[str] = field(default_factory=list)  # JD keywords present in the final resume
    not_covered: list[str] = field(default_factory=list)
    coverage: float | None = None  # % of JD keywords present in the final resume
    warnings: list[str] = field(default_factory=list)
    resume_pages: int | None = None
    hr_score: int | None = None  # HR / ATS judge score out of 100 for the final resume
    hr_rounds: list[dict] = field(default_factory=list)  # every judged version: score, feedback, changes
    hr_pass_score: int | None = None


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


# Fact-check "claims" that are really about the future (what the candidate will do) are not errors.


def _unique_keywords(bullet: str, resume: Resume, keywords: list[str]) -> int:
    """How many JD keywords would disappear from the resume without this bullet."""
    ours = [k for k in keywords if has_keyword(k, bullet)]
    if not ours:
        return 0
    text = resume.as_text().replace(bullet, "", 1)
    return sum(not has_keyword(k, text) for k in ours)


def _trim_once(resume: Resume, base: Resume, keywords: list[str], preferred: set[str]) -> str | None:
    """Remove the lowest-value ADDED content to shorten the resume. Base content is never removed.

    Bullets in `preferred` (the planned additions) go last; keyword-gap bullets go first.
    """
    if len(resume.additional_info) > len(base.additional_info):
        return f"additional info '{resume.additional_info.pop()}'"
    if resume.education_notes:
        return f"education note '{resume.education_notes.pop()}'"
    # Added bullets are the trailing `added` bullets of each entry.
    candidates = []
    for entry in (*resume.experience, *resume.projects):
        floor = MIN_JD_PROJECT_BULLETS if isinstance(entry, Project) and entry.is_new else 0
        if entry.added > floor:
            for bullet in entry.bullets[len(entry.bullets) - entry.added:]:
                rank = (bullet in preferred, _unique_keywords(bullet, resume, keywords), -entry.added)
                candidates.append((rank, entry, bullet))
    if not candidates:
        return None
    _, entry, bullet = min(candidates, key=lambda c: c[0])
    entry.bullets.remove(bullet)
    entry.added -= 1
    return f"added bullet '{bullet}'"


def _combine(a: MergeReport, b: MergeReport) -> MergeReport:
    for kind, n in b.added.items():
        a.count(kind, n)
    a.dropped += b.dropped
    return a


def _sentences(text: str) -> list[str]:
    return [x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x]


def _keeps_base(summary: str, base_summary: str) -> bool:
    """Every base sentence is still present (allowing inserted phrases)."""
    merged = [norm(x) for x in _sentences(summary)]
    return all(
        any(SequenceMatcher(None, norm(b), m).ratio() >= SUMMARY_KEEP_RATIO for m in merged)
        for b in _sentences(base_summary)
    )


def _city(location: str) -> str:
    """'Munich, Germany' -> 'Munich'; '' for unknown or remote roles."""
    city = re.split(r"[,(/|;]| or ", location)[0].strip()
    city = re.sub(r"^(hybrid|on-?site|onsite)\s*[-:]?\s*", "", city, flags=re.I).strip()
    return "" if not city or "remote" in city.lower() else city


class TailoringPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.reflector = ResumeReflector(settings, self.llm)

    # ------------------------------------------------------------------ LLM steps

    def _plan(self, base: Resume, jd: str) -> JobPlan:
        """Understand the job and map its needs to the candidate's real evidence.

        Cached on disk per (base resume, JD, prompt): re-running the same JD skips this call.
        """
        base_text = base.as_text()
        digest = hashlib.sha256(f"{base_text}\n{jd}\n{PLAN_SYSTEM_PROMPT}".encode()).hexdigest()[:16]
        cache = self.settings.output_dir / ".cache" / f"plan_{digest}.json"
        if cache.exists():
            log.info("Using cached plan %s", cache.name)
            return JobPlan.model_validate_json(cache.read_text(encoding="utf-8"))
        plan = self.llm.structured(
            PLAN_SYSTEM_PROMPT,
            PLAN_USER_TEMPLATE.format(jd=jd),
            JobPlan,
            reasoning_effort=self.settings.writing_reasoning_effort,
            prefix=RESUME_PREFIX_TEMPLATE.format(base_resume=base_text),
        )
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(plan.model_dump_json(), encoding="utf-8")
        return plan

    def _additions(self, base: Resume, plan: JobPlan) -> ResumeAdditions:
        """Write the resume additions from the plan (the JD itself is summarised in the plan)."""
        adds = self.llm.structured(
            WRITE_SYSTEM_PROMPT,
            WRITE_USER_TEMPLATE.format(plan=plan.brief(), keywords=", ".join(plan.jd_keywords)),
            ResumeAdditions,
            reasoning_effort=self.settings.writing_reasoning_effort,
            prefix=RESUME_PREFIX_TEMPLATE.format(base_resume=base.as_text()),
        )
        adds.analysis = plan.analysis
        adds.jd_keywords = plan.jd_keywords
        adds.requirements_not_covered = plan.requirements_not_covered
        return adds

    def _summary(self, resume: Resume, adds: ResumeAdditions) -> str:
        pointers = [plain_text(p) for p in adds.summary_pointers if p.strip()]
        if not pointers:
            return resume.summary
        max_words = len(resume.summary.split()) + SUMMARY_EXTRA_WORDS
        merged = self.llm.structured(
            SUMMARY_SYSTEM_PROMPT_TEMPLATE.format(max_words=max_words),
            SUMMARY_USER_TEMPLATE.format(
                role=adds.analysis.role,
                company=adds.analysis.company or "the hiring company",
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
        if not _keeps_base(summary, resume.summary):
            log.warning("Merged summary dropped or rewrote base sentences; keeping base summary")
            return resume.summary
        return summary

    def _gap_fill(self, resume: Resume, adds: ResumeAdditions, report: MergeReport) -> Resume:
        """Extra rounds that place every JD keyword still missing from the resume."""
        for round_no in range(1, self.settings.coverage_rounds + 1):
            missing = missing_keywords(adds.jd_keywords, resume.as_text())
            if not missing:
                break
            log.info("Coverage round %d: %d missing keyword(s): %s", round_no, len(missing), missing)
            jd_project = next((p.name for p in resume.projects if p.is_new), "none")
            gap = _clean(self.llm.structured(
                GAP_FILL_SYSTEM_PROMPT,
                GAP_FILL_USER_TEMPLATE.format(
                    role=adds.analysis.role,
                    company=adds.analysis.company or "the hiring company",
                    company_profile=adds.analysis.company_profile or "not stated",
                    project=jd_project,
                    resume=resume.as_text(),
                    missing="\n".join(f"- {k}" for k in missing),
                    extra_skills=self.settings.extra_skills.strip() or "none",
                ),
                ResumeAdditions,
            ))
            gap.analysis = adds.analysis  # so the merge checks know the target company
            resume, round_report = merge(resume, gap)
            _combine(report, round_report)
            # Keywords the model refused to place without a false claim are reported, not forced.
            adds.requirements_not_covered += [
                k for k in gap.requirements_not_covered if k not in adds.requirements_not_covered
            ]
        return resume

    def _motivation(self, location: str) -> str:
        """Personal motivation for the cover letter, chosen by the job's city."""
        partner, home = self.settings.partner_term, self.settings.partner_city
        city = _city(location)
        if not city or key(home) in key(city):
            text = (
                f"My {partner} already lives in {home}, so this role lets me build my career in the "
                f"city where we are making our home, and I am committed to settling in {home} long term."
            )
        else:
            text = (
                f"My {partner} currently lives in {home}, and we plan to move to {city} together, "
                f"so I am committed to settling in {city} long term."
            )
        if extra := self.settings.relocation_motivation.strip():
            text += f" {extra}"
        return text

    def _drop_unsupported_numbers(self, letter: CoverLetter, source: str) -> tuple[CoverLetter, list[str]]:
        """Remove sentences whose numbers appear in neither the resume nor the JD (no LLM call)."""
        paragraphs, dropped = [], []
        for para in letter.paragraphs:
            sentences = _sentences(para)
            keep = [x for x in sentences if not unsupported_numbers(x, source)]
            if len(keep) == len(sentences) or not keep:   # never empty a paragraph
                paragraphs.append(para)
                if not keep:
                    dropped += [f"Cover letter: number(s) {unsupported_numbers(para, source)} not in the resume; check this paragraph"]
                continue
            dropped += [f"Cover letter: removed a sentence with a number not in the resume: {x}" for x in sentences if x not in keep]
            paragraphs.append(" ".join(keep))
        return CoverLetter(**{**letter.model_dump(), "paragraphs": paragraphs}), dropped

    def _ensure_motivation(self, letter: CoverLetter, location: str) -> CoverLetter:
        """Guarantee the personal motivation is in the letter, with the right cities."""
        text = " ".join(letter.paragraphs)
        city = _city(location)
        home = self.settings.partner_city
        has_partner = key(self.settings.partner_term) in key(text)
        has_cities = key(home) in key(text) and (not city or key(city) in key(text))
        if has_partner and has_cities:
            return letter
        log.warning("Cover letter lacks the personal motivation; inserting it into the last paragraph")
        paragraphs = list(letter.paragraphs)
        # Drop the model's own (wrong or partial) relocation sentences, then state the right one.
        partner = key(self.settings.partner_term)
        kept = [
            x for x in _sentences(paragraphs[-1])
            if partner not in key(x) and not re.search(r"relocat|move to|settl", x, re.I)
        ]
        paragraphs[-1] = " ".join([self._motivation(location), *kept])
        return CoverLetter(**{**letter.model_dump(), "paragraphs": paragraphs})

    def _cover_letter(self, resume: Resume, jd: str, plan: JobPlan) -> tuple[CoverLetter, list[str]]:
        resume_text = resume.as_text()
        prefix = LETTER_PREFIX_TEMPLATE.format(resume=resume.evidence_text())
        location = plan.analysis.location
        # Low reasoning: the plan already did the thinking (needs mapped to evidence). At medium
        # the reasoning often used up the output budget, wasting a whole failed attempt.
        letter = _clean(self.llm.structured(
            COVER_LETTER_SYSTEM_PROMPT,
            COVER_LETTER_USER_TEMPLATE.format(
                plan=plan.brief(),
                location=location or "not stated",
                motivation=self._motivation(location),
            ),
            CoverLetter,
            prefix=prefix,
        ))
        letter = self._ensure_motivation(letter, location)
        # One LLM call: the prompt carries the fact-check rules; numbers are verified in code.
        letter, notes = self._drop_unsupported_numbers(letter, f"{resume_text}\n{jd}")
        if notes:
            log.warning("Cover letter: %s", notes)
        return letter, notes

    # ------------------------------------------------------------------ output

    def _fit_pages(
        self, resume: Resume, base: Resume, keywords: list[str], preferred: set[str], tex_path: Path
    ) -> tuple[Resume, int, list[str]]:
        """Compile; while over the page limit, trim the lowest-value content."""
        trimmed: list[str] = []
        while True:
            tex_path.write_text(render_resume(resume, self.settings), encoding="utf-8")
            pages = pdf_page_count(compile_pdf(tex_path, self.settings))
            if pages <= self.settings.max_resume_pages:
                break
            # Trim two items per compile to keep the loop short.
            removed = [r for r in (_trim_once(resume, base, keywords, preferred) for _ in range(2)) if r]
            if not removed:
                break
            trimmed += removed
            log.info("Resume is %d pages; trimmed %s", pages, removed)
        return resume, pages, trimmed

    def run(self, jd_text: str, company: str | None = None, city: str | None = None) -> GenerationResult:
        """Generate both documents. `company` and `city` override what is detected from the JD."""
        jd_text = jd_text.strip()
        company = (company or "").strip()
        city = (city or "").strip()
        if len(jd_text) < self.settings.min_jd_chars:
            raise DocumentError(
                f"The job description is too short ({len(jd_text)} characters). "
                "Paste or upload the full JD."
            )

        base = load_base(self.settings.base_resume_path, self.settings.base_resume_fixes)
        log.info("JD %d chars", len(jd_text))

        plan = _clean(self._plan(base, jd_text))
        if company:
            plan.analysis.company = company
        if city:
            plan.analysis.location = city  # drives the cover letter's relocation paragraph
        elif not _city(plan.analysis.location):
            log.warning("No job city given or found in the JD; the cover letter assumes %s", self.settings.partner_city)
        log.info("Plan: %s", plan.brief())
        adds = _clean(self._additions(base, plan))
        company = plan.analysis.company or ""
        resume, report = merge(base, adds)
        if headline := _aligned_headline(base, adds.headline):
            resume.headline = headline  # job title alignment counts toward the ATS score
        if not company:
            report.dropped.append(
                "The JD does not name the company. Enter it in the Company field for a sharper project and letter."
            )
        if not any(p.is_new for p in resume.projects):
            report.dropped.append("No company-specific project was added for this JD.")
        planned = {b for e in (*resume.experience, *resume.projects) for b in e.bullets}
        resume = self._gap_fill(resume, adds, report)

        hr_score, hr_rounds = None, []
        if self.settings.judge_enabled:
            try:
                resume, rounds, lacking = self.reflector.run(resume, adds, jd_text, report)
            except LLMError as exc:
                log.warning("HR judge failed; keeping the resume as is: %s", exc)
                report.dropped.append(f"HR / ATS review could not run: {exc}")
            else:
                hr_score, hr_rounds = max(r.score for r in rounds), [asdict(r) for r in rounds]
                adds.requirements_not_covered += [k for k in lacking if k not in adds.requirements_not_covered]
                if hr_score < INTERVIEW_SCORE:
                    best = next(r for r in rounds if r.outcome == "selected")
                    report.dropped.append(
                        f"HR / ATS review: {hr_score}/100, below the "
                        f"{INTERVIEW_SCORE} an interview usually needs. Main gaps: " + "; ".join(best.gaps[:3])
                    )

        # Summary (light model) and cover letter (main model) use separate rate-limit buckets.
        with ThreadPoolExecutor(max_workers=2) as pool:
            summary_future = pool.submit(self._summary, resume, adds)
            letter_future = pool.submit(self._cover_letter, resume, jd_text, plan)
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
            resume, pages, trimmed = self._fit_pages(resume, base, adds.jd_keywords, planned, resume_tex)
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

        final_text = resume.as_text()
        missing = missing_keywords(adds.jd_keywords, final_text)
        unique = {key(k): k.strip() for k in reversed(adds.jd_keywords) if key(k)}
        keywords = [k for k in reversed(unique.values()) if has_keyword(k, final_text)]
        # One entry per term, and nothing the final resume already contains.
        not_covered = list(dict.fromkeys(
            k.strip() for k in missing + adds.requirements_not_covered if key(k) and not has_keyword(k, final_text)
        ))
        total = len(keywords) + len(missing)
        coverage = round(100 * len(keywords) / total, 1) if total else None
        log.info("JD keyword coverage: %s%% (%d/%d); missing %s", coverage, len(keywords), total, missing)

        result = GenerationResult(
            job_id=job_id,
            company=company,
            role=adds.analysis.role,
            industry=adds.analysis.industry,
            location=adds.analysis.location,
            files=files,
            added=report.added,
            keywords=keywords,
            not_covered=not_covered,
            coverage=coverage,
            warnings=warnings,
            resume_pages=pages,
            hr_score=hr_score,
            hr_rounds=hr_rounds,
            hr_pass_score=self.settings.judge_pass_score if hr_score is not None else None,
        )
        (out / "report.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        log.info("Job %s complete: %s", job_id, files)
        return result
