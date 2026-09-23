"""Parse the base resume PDF into a structured `Resume` (the constant half of the output)."""

import logging
import re
from functools import lru_cache
from pathlib import Path

from .documents import DocumentError, load_base_resume
from .schemas import Education, Experience, Project, Resume, SkillGroup
from .text import plain_text

log = logging.getLogger(__name__)

SECTIONS = (
    "SUMMARY",
    "TECHNICAL SKILLS",
    "PROFESSIONAL EXPERIENCE",
    "PROJECTS",
    "EDUCATION",
    "LANGUAGES",
    "ADDITIONAL INFORMATION",
)
REQUIRED_SECTIONS = ("SUMMARY", "TECHNICAL SKILLS", "PROFESSIONAL EXPERIENCE", "PROJECTS", "EDUCATION")
_DATES = r"\s*(?:\| )?(?P<start>\w{3} \d{4}) - (?P<end>\w{3} \d{4}|Present)$"
# "Title | Company Location | dates" (old layout) or "Title | Company | LocationDates" (new layout).
_ROLE_RE = re.compile(
    r"^(?P<title>.+?) \| (?P<company>.+?)(?: \|)? (?P<location>[A-Z][\w.]+, [A-Z]\w+)" + _DATES
)
_EDU_RE = re.compile(r"^(?P<degree>.+?) \| (?P<institution>.+?)" + _DATES)
_SKILL_RE = re.compile(r"^(?P<category>[A-Za-z][A-Za-z /&-]{1,40}): ?(?P<items>.+)$")
_PROJECT_SEP_RE = re.compile(r" [—–] ")
# Second halves of real compound words; any other line-end hyphen is LaTeX hyphenation.
_COMPOUND_TAILS = {
    "based", "driven", "powered", "grade", "level", "time", "aware", "facing", "specific",
    "scale", "end", "agent", "like", "first", "oriented", "centric", "making", "term", "source",
    "commerce", "learning", "context", "switching", "ready", "tuning", "shot", "free",
}
# PDF lines where the spaces were squeezed out ("DevelopedaPython-andFlask-basedparser").
_GLUED_RE = re.compile(r"[A-Za-z-]{30,}")


def _join(prev: str, nxt: str) -> str:
    """Join a wrapped PDF line to the previous one, undoing LaTeX hyphenation."""
    if re.search(r"[a-z]-$", prev) and nxt[:1].islower():
        tail = re.match(r"[a-z]+", nxt)
        if tail and tail.group() in _COMPOUND_TAILS:
            return prev + nxt
        return prev[:-1] + nxt
    return f"{prev} {nxt}"


def _dashes(line: str) -> str:
    return re.sub(r"\s*[–—]\s*(?=\w{3} \d{4}$|Present$)", " - ", line)


def _split_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    header, sections, current = [], {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.isdigit():  # blank lines and page numbers
            continue
        if line in SECTIONS:
            current = line
            sections[current] = []
        elif current is None:
            header.append(line)
        else:
            sections[current].append(line)
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    if missing:
        raise DocumentError(f"Base resume is missing sections: {', '.join(missing)}")
    return header, sections


def _bullets(lines: list[str], is_header) -> list[tuple[str, list[str]]]:
    """Group lines into (header, bullets); wrapped bullet lines are joined.

    A non-bullet line after a finished bullet (ending in ".") starts a new entry, so
    headers without a separator (e.g. a project name alone on its line) are detected.
    """
    groups: list[tuple[str, list[str]]] = []
    for line in lines:
        if line.startswith("•"):
            groups[-1][1].append(line.lstrip("• ").strip())
        elif is_header(line) or not groups or not groups[-1][1] or groups[-1][1][-1].endswith("."):
            groups.append((line, []))
        else:
            groups[-1][1][-1] = _join(groups[-1][1][-1], line)
    return groups


def parse_resume_text(text: str) -> Resume:
    header, sec = _split_sections(text)
    for line in text.splitlines():
        if _GLUED_RE.search(line):
            log.warning(
                "Base resume line has words without spaces (fix the PDF or add it to BASE_RESUME_FIXES): %s",
                line.strip(),
            )

    skills: list[SkillGroup] = []
    wrapped_mid_item = False
    for line in sec["TECHNICAL SKILLS"]:
        m = _SKILL_RE.match(line)
        if m:
            skills.append(SkillGroup(category=m["category"].strip(), items=[]))
            rest = m["items"]
        elif skills:
            rest = line
        else:
            continue
        items = [i.strip() for i in rest.split(",")]
        # A wrapped line continues the previous item unless the PDF broke the line after a comma.
        if m is None and wrapped_mid_item and skills[-1].items:
            skills[-1].items[-1] = _join(skills[-1].items[-1], items.pop(0))
        skills[-1].items += [i for i in items if i]
        wrapped_mid_item = not rest.rstrip().endswith(",")

    experience = []
    for head, bullets in _bullets(sec["PROFESSIONAL EXPERIENCE"], lambda l: bool(_ROLE_RE.match(_dashes(l)))):
        m = _ROLE_RE.match(_dashes(head))
        if not m:
            raise DocumentError(f"Could not parse experience header: {head!r}")
        experience.append(Experience(**m.groupdict(), bullets=bullets))

    projects = []
    for head, bullets in _bullets(sec["PROJECTS"], lambda l: bool(_PROJECT_SEP_RE.search(l))):
        name, meta = (_PROJECT_SEP_RE.split(head, maxsplit=1) + [""])[:2]
        projects.append(Project(name=name.strip(), meta=meta.strip(), bullets=bullets))

    education = [Education(**m.groupdict()) for l in sec["EDUCATION"] if (m := _EDU_RE.match(_dashes(l)))]
    languages = [l for l in sec.get("LANGUAGES", []) if not l.startswith("•")]
    additional = [l.lstrip("• ").strip() for l in sec.get("ADDITIONAL INFORMATION", []) if l.startswith("•")]

    summary = ""
    for line in sec["SUMMARY"]:
        summary = _join(summary, line) if summary else line

    resume = Resume(
        headline=header[1] if len(header) > 1 else "Senior AI Engineer",
        summary=summary,
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
        languages=languages,
        additional_info=additional,
    )
    if not (resume.skills and resume.experience and resume.projects and resume.education):
        raise DocumentError("Base resume could not be parsed into skills, experience, projects and education.")
    return _clean_resume(resume)


def _clean_resume(resume: Resume) -> Resume:
    data = resume.model_dump()

    def walk(node):
        if isinstance(node, str):
            return plain_text(node)
        if isinstance(node, list):
            return [walk(n) for n in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return Resume.model_validate(walk(data))


@lru_cache(maxsize=4)
def _parse_cached(path: Path, mtime: float, fixes: tuple[tuple[str, str], ...]) -> Resume:
    text = load_base_resume(path)
    for find, replace in fixes:
        text = text.replace(find, replace)
    return parse_resume_text(text)


def load_base(path: Path, fixes: dict[str, str] | None = None) -> Resume:
    """Structured base resume, cached until the PDF changes on disk.

    `fixes` maps exact extracted text to its correction (for PDF extraction glitches).
    """
    if not path.exists():
        raise DocumentError(f"Base resume not found: {path}")
    return _parse_cached(path, path.stat().st_mtime, tuple(sorted((fixes or {}).items()))).model_copy(deep=True)
