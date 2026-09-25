"""Reflection loop (LangGraph): an HR / ATS judge scores the tailored resume, a revision improves it.

    judge --score >= pass mark or revisions used up--> END
      ^                    |
      |                    v
      +------------------ revise

The judge plays the target company's recruiter and scores the resume on a fixed rubric (tech
stack, relevant experience, the company-specific project, ATS keywords, credibility). Below the
pass mark, its gaps and fixes go to a revision call whose output passes through the same `merge`
checks as every other addition, so revisions cannot invent numbers or move tools between roles.
Every revision starts from the best-scoring resume so far, and the best one is returned.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .config import Settings
from .llm import LLMClient, LLMError
from .merge import MergeReport, merge
from .prompts import JUDGE_SYSTEM_PROMPT, JUDGE_USER_TEMPLATE, REFLECT_SYSTEM_PROMPT, REFLECT_USER_TEMPLATE
from .schemas import JobAnalysis, JudgeVerdict, Resume, ResumeAdditions
from .text import key, missing_keywords, plain_text

log = logging.getLogger(__name__)

# criterion -> (max points, what the recruiter checks). Points sum to 100.
RUBRIC: dict[str, tuple[int, str]] = {
    "tech_stack": (30, "The JD's languages, frameworks, cloud and tools appear in skills AND are used in the bullets of roles or projects."),
    "experience": (25, "Roles and projects show the same kind of work at the level the JD asks for (seniority, ownership, production delivery)."),
    "company_project": (20, "The company-specific project solves a believable problem of THIS company's product or domain (see company profile) with the JD's stack."),
    "ats_keywords": (15, "The JD's exact terms appear, in context and not only in the skills list; standard section headings; job title alignment."),
    "credibility": (10, "Concrete outcomes, consistent timeline, no filler or claims that look inflated."),
}
LABELS = {
    "tech_stack": "Tech stack",
    "experience": "Experience",
    "company_project": "Company project",
    "ats_keywords": "ATS keywords",
    "credibility": "Credibility",
}
# Added bullets per past role across all steps; more reads as invented and costs page space.
MAX_ADDED_PER_ROLE = 4
RUBRIC_TEXT = "\n".join(f"- {name} ({pts}): {desc}" for name, (pts, desc) in RUBRIC.items())


def total_score(verdict: JudgeVerdict) -> int:
    """Rubric total out of 100; each criterion is capped at its maximum."""
    return sum(min(getattr(verdict, name).score, pts) for name, (pts, _) in RUBRIC.items())


def _losses(verdict: JudgeVerdict) -> str:
    """Points lost per criterion, biggest loss first: where a revision gains the most."""
    lost = sorted(((pts - min(getattr(verdict, n).score, pts), n, pts) for n, (pts, _) in RUBRIC.items()), reverse=True)
    return "\n".join(f"- {LABELS[n]}: -{loss} of {pts}. {getattr(verdict, n).reason}" for loss, n, pts in lost if loss)


# Title words that claim more seniority than a role title; the JD title is used only if the
# resume's own headline or role titles already show them.
SENIORITY_WORDS = ("staff", "principal", "lead", "head", "director", "manager", "vp", "chief", "distinguished", "architect")
# "(m/w/d)", "(f/m/x)", "(all genders)"... are job-ad tags, not part of the title.
_GENDER_TAG_RE = re.compile(r"\s*[(\[]\s*(?:[a-z]{1,3}\s*/\s*){1,3}[a-z.]{1,4}\s*[)\]]|\s*\(all genders\)", re.I)


def _aligned_headline(base: Resume, proposed: str) -> str | None:
    """The JD's job title as the headline (role titles below stay unchanged), unless it claims
    seniority the resume does not show."""
    title = plain_text(_GENDER_TAG_RE.sub("", proposed)).strip(" |-,")
    if not title or key(title) == key(base.headline) or len(title) > 60:
        return None
    shown = " ".join([base.headline, *(e.title for e in base.experience)]).lower()
    if over := [w for w in SENIORITY_WORDS if re.search(rf"\b{w}\b", title, re.I) and not re.search(rf"\b{w}\b", shown)]:
        log.info("Headline '%s' not used: the resume shows no %s title", title, "/".join(over))
        return None
    return title


def review_text(verdict: JudgeVerdict) -> str:
    lines = [
        f"- {name}: {min(getattr(verdict, name).score, pts)}/{pts}. {getattr(verdict, name).reason}"
        for name, (pts, _) in RUBRIC.items()
    ]
    lines.append(f"Decision: {verdict.decision}")
    lines += [f"Gap: {g}" for g in verdict.gaps]
    lines += [f"Fix: {f}" for f in verdict.fixes]
    return "\n".join(lines)


@dataclass
class Round:
    """One judged version of the resume, for the UI's review journey."""

    label: str  # "First draft", "Revision 1", ...
    score: int
    decision: str
    breakdown: list[dict] = field(default_factory=list)  # {"name", "score", "max", "reason"}
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)  # what the revision changed before this review
    outcome: str = ""  # "revise", "discarded" or "selected"
    note: str = ""  # why


def _changes(before: Resume, after: Resume) -> list[str]:
    """Human-readable diff of a revision."""
    out = []
    old_skills = {i for g in before.skills for i in g.items}
    if new := [i for g in after.skills for i in g.items if i not in old_skills]:
        out.append("Added skills: " + ", ".join(new))
    old_bullets = {b for e in before.experience for b in e.bullets}
    for e in after.experience:
        out += [f"New bullet at {e.company}: {b}" for b in e.bullets if b not in old_bullets]
    if after.headline != before.headline:
        out.append(f"Headline: '{before.headline}' -> '{after.headline}'")
    old_project_bullets = {b for p in before.projects if not p.is_new for b in p.bullets}
    for p in after.projects:
        if not p.is_new:
            out += [f"New bullet in project {p.name}: {b}" for b in p.bullets if b not in old_project_bullets]
    old_proj = next((p for p in before.projects if p.is_new), None)
    new_proj = next((p for p in after.projects if p.is_new), None)
    if new_proj and (old_proj is None or old_proj.bullets != new_proj.bullets):
        verb = "Rewrote" if old_proj else "Added"
        out.append(f"{verb} company project '{new_proj.name}': " + " ".join(new_proj.bullets))
    return out or ["No change passed the truthfulness checks."]


class ReflectionState(TypedDict, total=False):
    resume: Resume  # latest candidate
    best: Resume  # highest-scoring resume so far
    best_score: int
    verdict: JudgeVerdict  # verdict for `best`
    revisions: int
    history: list[Round]
    not_covered: list[str]
    changes: list[str]  # diff of the latest revision, shown in its round
    pending: dict[str, int]  # what the latest revision added, counted only if it is kept
    stopped: bool  # a revision call failed; keep the best resume
    stale: int  # revisions in a row that did not raise the score
    unchanged: bool  # the latest revision changed nothing, so it is not judged
    failed: list[str]  # changes from discarded revisions, so they are not tried again


class ResumeReflector:
    def __init__(self, settings: Settings, llm: LLMClient):
        self.settings = settings
        self.llm = llm
        graph = StateGraph(ReflectionState)
        graph.add_node("judge", self._judge)
        graph.add_node("revise", self._revise)
        graph.add_edge(START, "judge")
        graph.add_conditional_edges("judge", self._route, {"revise": "revise", "done": END})
        graph.add_conditional_edges("revise", self._after_revise, {"judge": "judge", "revise": "revise", "done": END})
        self.graph = graph.compile()

    def run(
        self, resume: Resume, adds: ResumeAdditions, jd: str, report: MergeReport, max_revisions: int | None = None
    ) -> tuple[Resume, list[Round], list[str]]:
        """Judge and revise; returns the best resume, the score per round and new uncovered needs.
        max_revisions=0 only judges (subtle mode: the resume is not rewritten after the judge)."""
        self._adds, self._jd, self._report = adds, jd, report
        self._max_revisions = self.settings.judge_max_revisions if max_revisions is None else max_revisions
        state = self.graph.invoke(
            {"resume": resume, "best": resume, "best_score": -1, "revisions": 0, "history": [], "not_covered": [],
             "stale": 0, "failed": []}
        )
        history = state["history"]
        self._annotate(history, state["best_score"], state["revisions"])
        return state["best"], history, state["not_covered"]

    def _annotate(self, history: list[Round], best_score: int, revisions: int) -> None:
        """Mark each round: sent back for revision, discarded, or selected (and why)."""
        pass_score = self.settings.judge_pass_score
        chosen = next(i for i, r in enumerate(history) if r.score == best_score)
        best_so_far = -1
        for i, r in enumerate(history):
            if i == chosen:
                r.outcome = "selected"
                if r.score >= pass_score:
                    r.note = f"Selected: {r.score}/100 reaches the {pass_score} target."
                elif revisions == 0:
                    r.note = f"Selected: {r.score}/100; the revision step could not run."
                else:
                    r.note = (
                        f"Selected: highest score after {revisions} revision(s), below the {pass_score} "
                        "target. Further gains need experience the resume does not show."
                    )
            elif r.score <= best_so_far:
                r.outcome = "discarded"
                r.note = f"Discarded: {r.score}/100 is not better than {best_so_far}/100, the previous version was kept."
            else:
                r.outcome = "revise"
                r.note = f"Below the {pass_score} target: sent back with the lost points as feedback."
            best_so_far = max(best_so_far, r.score)

    # ------------------------------------------------------------------ nodes

    @property
    def _analysis(self) -> JobAnalysis:
        return self._adds.analysis

    def _judge(self, state: ReflectionState) -> ReflectionState:
        a = self._analysis
        company = a.company or "the hiring company"
        verdict = self.llm.structured(
            JUDGE_SYSTEM_PROMPT.format(company=company, rubric=RUBRIC_TEXT),
            JUDGE_USER_TEMPLATE.format(
                role=a.role,
                company=company,
                company_profile=a.company_profile or "not stated",
                jd=self._jd,
                resume=state["resume"].as_text(),
            ),
            JudgeVerdict,
            reasoning_effort=self.settings.writing_reasoning_effort,
            temperature=0.0,  # same resume, same score: differences come from the revision
        )
        score = total_score(verdict)
        n = state["revisions"]  # revisions that changed nothing are not judged, so count revisions
        history = [*state["history"], Round(
            label="First draft" if n == 0 else f"Revision {n}",
            score=score,
            decision=verdict.decision,
            breakdown=[
                {"name": LABELS[name], "score": min(getattr(verdict, name).score, pts), "max": pts,
                 "reason": getattr(verdict, name).reason}
                for name, (pts, _) in RUBRIC.items()
            ],
            strengths=verdict.strengths[:4],
            gaps=verdict.gaps[:5],
            changes=state.get("changes", []),
        )]
        log.info("HR judge round %d: %d/100 (%s); gaps: %s", len(history), score, verdict.decision, verdict.gaps)
        if score > state["best_score"]:
            for kind, n in state.get("pending", {}).items():
                self._report.count(kind, n)
            return {"best": state["resume"], "best_score": score, "verdict": verdict, "history": history, "stale": 0}
        log.info("Revision scored %d, not above %d; keeping the previous resume", score, state["best_score"])
        return {"history": history, "stale": state["stale"] + 1, "failed": [*state["failed"], *state.get("changes", [])]}

    def _after_revise(self, state: ReflectionState) -> str:
        if state.get("stopped"):
            return "done"
        if state.get("unchanged"):  # same resume as the best: re-judging it would only measure noise
            return self._route(state)
        return "judge"

    def _route(self, state: ReflectionState) -> str:
        if state["best_score"] >= self.settings.judge_pass_score:
            return "done"
        if state["revisions"] >= self._max_revisions:
            return "done"
        if state["stale"] >= self.settings.judge_patience:
            log.info("No improvement in %d revisions; stopping at %d/100", state["stale"], state["best_score"])
            return "done"
        return "revise"

    def _revise(self, state: ReflectionState) -> ReflectionState:
        a = self._analysis
        best = state["best"]
        jd_project = next((p for p in best.projects if p.is_new), None)
        try:
            fix = self.llm.structured(
                REFLECT_SYSTEM_PROMPT,
                REFLECT_USER_TEMPLATE.format(
                    role=a.role,
                    company=a.company or "the hiring company",
                    company_profile=a.company_profile or "not stated",
                    missing=", ".join(missing_keywords(self._adds.jd_keywords, best.as_text())) or "none",
                    score=state["best_score"],
                    target=self.settings.judge_pass_score,
                    losses=_losses(state["verdict"]),
                    review=review_text(state["verdict"]),
                    failed="\n".join(f"- {c}" for c in state["failed"][-8:]) or "none",
                    headline=best.headline,
                    extra_skills=self.settings.extra_skills.strip() or "none",
                    resume=best.as_text(),
                ),
                ResumeAdditions,
                reasoning_effort=self.settings.writing_reasoning_effort,
            )
        except LLMError as exc:
            log.warning("Reflection revision failed; keeping the current resume: %s", exc)
            return {"stopped": True}

        fix.analysis = a  # so the merge checks know the target company
        base = best
        if fix.new_project and fix.new_project.bullets and jd_project is not None:
            # A rewrite replaces the company-specific project (generated content, never base content).
            base = best.model_copy(deep=True)
            base.projects = [p for p in base.projects if not p.is_new]
        revised, round_report = merge(base, fix)
        if headline := _aligned_headline(best, fix.headline):
            revised.headline = headline
        for e in revised.experience:
            while e.added > MAX_ADDED_PER_ROLE:
                log.info("%s at %s: dropped revision bullet over the %d-bullet cap", e.title, e.company, MAX_ADDED_PER_ROLE)
                e.bullets.pop()
                e.added -= 1
                round_report.added["experience bullets"] = max(0, round_report.added.get("experience bullets", 0) - 1)
        if jd_project is not None and not any(p.is_new for p in revised.projects):
            log.info("Project rewrite was rejected by the merge checks; keeping the previous project")
            revised.projects.insert(1, jd_project.model_copy(deep=True))

        new_gaps = [k for k in fix.requirements_not_covered if k not in state["not_covered"]]
        if revised.model_dump() == best.model_dump():
            log.info("Revision %d: no change passed the checks; not re-judged", state["revisions"] + 1)
            return {
                "revisions": state["revisions"] + 1,
                "stale": state["stale"] + 1,
                "unchanged": True,
                "not_covered": [*state["not_covered"], *new_gaps],
            }
        return {
            "unchanged": False,
            "resume": revised,
            "changes": _changes(best, revised),
            "revisions": state["revisions"] + 1,
            # A rewrite replaces the company project; it is not another one.
            "pending": {k: n for k, n in round_report.added.items() if k != "new project" or jd_project is None},
            "not_covered": [*state["not_covered"], *new_gaps],
        }
