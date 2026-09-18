"""Parse the base resume PDF into a structured `Resume` (the constant half of the output)."""

import re
from functools import lru_cache
from pathlib import Path

from .documents import DocumentError, load_base_resume
from .schemas import Education, Experience, Project, Resume, SkillGroup
from .text import plain_text

SECTIONS = (
    "SUMMARY",
    "TECHNICAL SKILLS",
    "PROFESSIONAL EXPERIENCE",
    "PROJECTS",
    "EDUCATION",
    "ADDITIONAL INFORMATION",
)
_ROLE_RE = re.compile(
    r"^(?P<title>.+?) \| (?P<company>.+) (?P<location>[A-Z][\w.]+, [A-Z]\w+) \| "
    r"(?P<start>\w{3} \d{4}) - (?P<end>\w{3} \d{4}|Present)$"
)
_EDU_RE = re.compile(
    r"^(?P<degree>.+?) \| (?P<institution>.+?) \| (?P<start>\w{3} \d{4}) - (?P<end>\w{3} \d{4}|Present)$"
)
_SKILL_RE = re.compile(r"^(?P<category>[A-Za-z][A-Za-z /&-]{1,40}): (?P<items>.+)$")


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
    missing = [s for s in SECTIONS[:5] if s not in sections]
    if missing:
        raise DocumentError(f"Base resume is missing sections: {', '.join(missing)}")
    return header, sections


def _bullets(lines: list[str], is_header) -> list[tuple[str, list[str]]]:
    """Group lines into (header, bullets); wrapped bullet lines are joined."""
    groups: list[tuple[str, list[str]]] = []
    for line in lines:
        if line.startswith("•"):
            groups[-1][1].append(line.lstrip("• ").strip())
        elif is_header(line) or not groups or not groups[-1][1]:
            groups.append((line, []))
        else:
            groups[-1][1][-1] += " " + line
    return groups


def parse_resume_text(text: str) -> Resume:
    header, sec = _split_sections(text)

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
            skills[-1].items[-1] += " " + items.pop(0)
        skills[-1].items += [i for i in items if i]
        wrapped_mid_item = not rest.rstrip().endswith(",")

    experience = []
    for head, bullets in _bullets(sec["PROFESSIONAL EXPERIENCE"], lambda l: bool(_ROLE_RE.match(l))):
        m = _ROLE_RE.match(head)
        if not m:
            raise DocumentError(f"Could not parse experience header: {head!r}")
        experience.append(Experience(**m.groupdict(), bullets=bullets))

    projects = []
    for head, bullets in _bullets(sec["PROJECTS"], lambda l: " — " in l):
        name, _, meta = head.partition(" — ")
        projects.append(Project(name=name.strip(), meta=meta.strip(), bullets=bullets))

    education = [Education(**m.groupdict()) for l in sec["EDUCATION"] if (m := _EDU_RE.match(l))]
    additional = [l.lstrip("• ").strip() for l in sec.get("ADDITIONAL INFORMATION", []) if l.startswith("•")]

    resume = Resume(
        headline=header[1] if len(header) > 1 else "Senior AI Engineer",
        summary=" ".join(sec["SUMMARY"]),
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
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
def _parse_cached(path: Path, mtime: float) -> Resume:
    return parse_resume_text(load_base_resume(path))


def load_base(path: Path) -> Resume:
    """Structured base resume, cached until the PDF changes on disk."""
    if not path.exists():
        raise DocumentError(f"Base resume not found: {path}")
    return _parse_cached(path, path.stat().st_mtime).model_copy(deep=True)
