"""Merge LLM-generated additions into the constant base resume.

Every addition is sanitised and checked before insertion:
duplicates are skipped, names are matched to existing roles/projects,
and bullets with numbers that do not exist in the base resume are dropped.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches

from .schemas import Experience, Project, Resume, ResumeAdditions, SkillGroup
from .text import key, norm, plain_text, unsupported_numbers

log = logging.getLogger(__name__)

DUPLICATE_RATIO = 0.82
# Share of a new bullet's content words already in one existing bullet that makes it a restatement.
RESTATE_OVERLAP = 0.6
NAME_MATCH_RATIO = 0.6
# More new bullets than this under one past role starts to read as invented (the page is limited too).
MAX_NEW_BULLETS_PER_ROLE = 2
# The JD-specific project stays concise.
MAX_JD_PROJECT_BULLETS = 2
# Scale words the model likes to invent; a new bullet may use them only if the resume does.
SCALE_RE = re.compile(r"\b(millions?|billions?|thousands|daily|per day|hourly|petabytes?|terabytes?)\b", re.I)
# Skill categories holding concrete platforms/tools. A new bullet under a past role may name one
# only if that role's own bullets already do (the model likes to move tools between employers).
PLATFORM_CATEGORY_RE = re.compile(r"mlops|cloud|observab|search|database|platform|bi|testing|devops|infra", re.I)
_STOPWORDS = {
    "the", "and", "for", "with", "that", "into", "from", "using", "across", "via", "its", "their",
    "this", "was", "were", "of", "to", "a", "an", "in", "on", "by", "as", "at", "or", "is", "be",
}


@dataclass
class MergeReport:
    added: dict[str, int] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)

    def count(self, kind: str, n: int = 1) -> None:
        self.added[kind] = self.added.get(kind, 0) + n


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def _name_score(a: str, b: str) -> float:
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return 0.0
    if ka in kb or kb in ka:
        return 1.0
    prefix = 0
    for x, y in zip(ka, kb):
        if x != y:
            break
        prefix += 1
    return 1.0 if prefix >= 6 else SequenceMatcher(None, ka, kb).ratio()


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def _restates(bullet: str, existing: str) -> bool:
    new = _words(bullet)
    return bool(new) and len(new & _words(existing)) / len(new) >= RESTATE_OVERLAP


def _has_term(term: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text.lower()) is not None


def _best(name: str, candidates: list[str]) -> int | None:
    scores = [_name_score(name, c) for c in candidates]
    if not scores or max(scores) < NAME_MATCH_RATIO:
        return None
    return scores.index(max(scores))


class _BulletFilter:
    """Rejects restated, duplicated or embellished bullets.

    New bullets carry no numbers (the base bullets already hold the real metrics, and the
    model tends to move them to other work), no invented scale words, and never name the
    target company (a project "for Catawiki" reads as if the candidate worked there).
    """

    def __init__(self, base: Resume, report: MergeReport, company: str = ""):
        self.source = base.as_text()
        self.seen = [b for e in base.experience for b in e.bullets] + [b for p in base.projects for b in p.bullets]
        self.report = report
        self.company = key(company)

    def accept(
        self, bullet: str, where: str, entry_bullets: list[str] = (), platforms: set[str] = frozenset()
    ) -> str | None:
        bullet = plain_text(bullet).rstrip()
        if len(bullet) < 15:
            return None
        if bullet[-1] not in ".!":
            bullet += "."
        entry_text = " ".join(entry_bullets)
        if bad := unsupported_numbers(bullet, entry_text):
            log.info(f"{where}: dropped bullet with numbers not from this entry ({', '.join(bad)}): {bullet}")
            return None
        if (m := SCALE_RE.search(bullet)) and m.group().lower() not in self.source.lower():
            log.info(f"{where}: dropped bullet with an unsupported scale claim ('{m.group()}'): {bullet}")
            return None
        if moved := [t for t in platforms if _has_term(t, bullet) and not _has_term(t, entry_text)]:
            log.info(f"{where}: dropped bullet using tools not shown for this role ({', '.join(sorted(moved))}): {bullet}")
            return None
        if len(self.company) > 2 and self.company in key(bullet):
            log.info(f"{where}: dropped bullet naming the target company: {bullet}")
            return None
        if any(_similar(bullet, s) >= DUPLICATE_RATIO or _restates(bullet, s) for s in self.seen):
            log.info("%s: skipped bullet that restates an existing one: %s", where, bullet)
            return None
        self.seen.append(bullet)
        return bullet


def merge(base: Resume, adds: ResumeAdditions) -> tuple[Resume, MergeReport]:
    resume = base.model_copy(deep=True)
    report = MergeReport()
    bullets = _BulletFilter(base, report, adds.analysis.company)

    # --- skills --------------------------------------------------------------
    existing = {key(i) for g in resume.skills for i in g.items}
    categories = {key(g.category): g for g in resume.skills}
    for s in adds.skills_to_add:
        skill = plain_text(s.skill).strip(" .")
        if not skill or key(skill) in existing:
            continue
        cat_key = key(s.category)
        group = categories.get(cat_key)
        if group is None:
            close = get_close_matches(cat_key, list(categories), n=1, cutoff=0.6)
            group = categories[close[0]] if close else None
        if group is None:
            group = categories.get(key("Additional"))
            if group is None:
                group = SkillGroup(category="Additional", items=[])
                resume.skills.append(group)
                categories[key("Additional")] = group
        group.items.append(skill)
        existing.add(key(skill))
        report.count("skills")

    # --- experience ----------------------------------------------------------
    base_added = {id(e): 0 for e in resume.experience}
    platforms = {
        i for g in resume.skills if PLATFORM_CATEGORY_RE.search(g.category) for i in g.items if len(i) > 2
    }
    for ptr in adds.experience_pointers:
        matches = [
            i for i, e in enumerate(resume.experience) if _name_score(ptr.company, e.company) >= NAME_MATCH_RATIO
        ]
        if not matches:
            report.dropped.append(f"Experience pointers for unknown company '{ptr.company}' were ignored.")
            continue
        role_idx = _best(ptr.role, [resume.experience[i].title for i in matches]) if ptr.role else None
        exp: Experience = resume.experience[matches[role_idx if role_idx is not None else 0]]
        for b in ptr.bullets:
            if exp.added - base_added.get(id(exp), 0) >= MAX_NEW_BULLETS_PER_ROLE:
                log.info("%s at %s: skipped extra bullet (limit %d): %s", exp.title, exp.company, MAX_NEW_BULLETS_PER_ROLE, b)
                continue
            if clean := bullets.accept(b, f"{exp.title} at {exp.company}", exp.bullets, platforms):
                exp.bullets.append(clean)
                exp.added += 1
                report.count("experience bullets")

    # --- projects ------------------------------------------------------------
    def add_to_project(name: str, new_bullets: list[str], technologies: list[str] = ()) -> bool:
        idx = _best(name, [p.name for p in resume.projects])
        if idx is None:
            return False
        proj: Project = resume.projects[idx]
        for b in new_bullets:
            if proj.is_new and len(proj.bullets) >= MAX_JD_PROJECT_BULLETS:
                log.info("%s: skipped extra bullet (limit %d): %s", proj.name, MAX_JD_PROJECT_BULLETS, b)
                break
            if clean := bullets.accept(b, proj.name, proj.bullets):
                proj.bullets.append(clean)
                proj.added += 1
                report.count("project bullets")
        known = {key(t) for t in proj.technologies}
        proj.technologies += [plain_text(t) for t in technologies if key(t) not in known]
        return True

    jd_project = next((p for p in resume.projects if p.is_new), None)
    for ptr in adds.existing_project_pointers:
        if not add_to_project(ptr.project, ptr.bullets):
            if jd_project is not None:  # gap-fill rounds: unknown names go to the JD project
                add_to_project(jd_project.name, ptr.bullets)
            else:
                report.dropped.append(f"Pointers for unknown project '{ptr.project}' were ignored.")

    if adds.new_project and adds.new_project.bullets:
        np = adds.new_project
        same_name = next((p for p in resume.projects if key(p.name) == key(np.name)), None)
        if jd_project is not None or same_name is not None:  # only one JD-specific project per resume
            add_to_project((jd_project or same_name).name, np.bullets, np.technologies)
        else:
            accepted = [c for b in np.bullets if (c := bullets.accept(b, np.name))][:MAX_JD_PROJECT_BULLETS]
            name = plain_text(np.name)
            if len(key(adds.analysis.company)) > 2 and key(adds.analysis.company) in key(name):
                name = re.sub(re.escape(adds.analysis.company), "", name, flags=re.I).strip(" -'s")
            if accepted:
                # JD-targeted project goes right after the flagship project.
                resume.projects.insert(1, Project(
                    name=name,
                    bullets=accepted,
                    technologies=[plain_text(t) for t in np.technologies],
                    added=len(accepted),
                    is_new=True,
                ))
                report.count("new project")

    # --- education / additional ----------------------------------------------
    edu_text = key(" ".join(f"{e.degree} {e.institution}" for e in resume.education))
    for note in adds.education_pointers:
        note = plain_text(note).strip()
        words = [w for w in note.replace(",", " ").split() if len(w) > 3]
        if not note or all(key(w) in edu_text for w in words):
            continue  # already shown in the education section
        resume.education_notes.append(note)
        report.count("education notes")

    for info in adds.charity_product_pointers:
        info = plain_text(info).strip()
        if info and all(_similar(info, a) < DUPLICATE_RATIO for a in resume.additional_info):
            resume.additional_info.append(info)
            report.count("additional info")

    log.info("Merged additions: %s; dropped %d", report.added, len(report.dropped))
    return resume, report
