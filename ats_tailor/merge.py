"""Merge LLM-generated additions into the constant base resume.

Every addition is sanitised and checked before insertion:
duplicates are skipped, names are matched to existing roles/projects,
and bullets with numbers that do not exist in the base resume are dropped.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches

from .schemas import Experience, Project, Resume, ResumeAdditions, SkillGroup
from .text import key, norm, plain_text, unsupported_numbers

log = logging.getLogger(__name__)

DUPLICATE_RATIO = 0.82
NAME_MATCH_RATIO = 0.6


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


def _best(name: str, candidates: list[str]) -> int | None:
    scores = [_name_score(name, c) for c in candidates]
    if not scores or max(scores) < NAME_MATCH_RATIO:
        return None
    return scores.index(max(scores))


class _BulletFilter:
    """Rejects duplicates of base/added bullets and bullets with invented numbers."""

    def __init__(self, base: Resume, report: MergeReport):
        self.source = base.as_text()
        self.seen = [b for e in base.experience for b in e.bullets] + [b for p in base.projects for b in p.bullets]
        self.report = report

    def accept(self, bullet: str, where: str) -> str | None:
        bullet = plain_text(bullet).rstrip()
        if len(bullet) < 15:
            return None
        if bullet[-1] not in ".!":
            bullet += "."
        if bad := unsupported_numbers(bullet, self.source):
            self.report.dropped.append(f"{where}: dropped bullet with numbers not in your resume ({', '.join(bad)}): {bullet}")
            return None
        if any(_similar(bullet, s) >= DUPLICATE_RATIO for s in self.seen):
            return None
        self.seen.append(bullet)
        return bullet


def merge(base: Resume, adds: ResumeAdditions) -> tuple[Resume, MergeReport]:
    resume = base.model_copy(deep=True)
    report = MergeReport()
    bullets = _BulletFilter(base, report)

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
            if clean := bullets.accept(b, f"{exp.title} at {exp.company}"):
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
            if clean := bullets.accept(b, proj.name):
                proj.bullets.append(clean)
                proj.added += 1
                report.count("project bullets")
        known = {key(t) for t in proj.technologies}
        proj.technologies += [plain_text(t) for t in technologies if key(t) not in known]
        return True

    for ptr in adds.existing_project_pointers:
        if not add_to_project(ptr.project, ptr.bullets):
            report.dropped.append(f"Pointers for unknown project '{ptr.project}' were ignored.")

    if adds.new_project and adds.new_project.bullets:
        np = adds.new_project
        if not add_to_project(np.name, np.bullets, np.technologies):
            accepted = [c for b in np.bullets if (c := bullets.accept(b, np.name))]
            if accepted:
                # JD-targeted project goes right after the flagship project.
                resume.projects.insert(1, Project(
                    name=plain_text(np.name),
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
