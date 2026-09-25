"""Data models.

Resume          - the base resume parsed from the PDF, and the final merged resume.
ResumeAdditions - what the LLM returns for a JD: only the new content.
"""

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- resume


class SkillGroup(BaseModel):
    category: str
    items: list[str]


class Experience(BaseModel):
    title: str
    company: str
    location: str
    start: str
    end: str
    bullets: list[str]
    added: int = 0  # number of trailing bullets that came from the LLM


class Project(BaseModel):
    name: str
    meta: str = ""
    bullets: list[str]
    technologies: list[str] = Field(default_factory=list)
    added: int = 0
    is_new: bool = False


class Education(BaseModel):
    degree: str
    institution: str
    start: str
    end: str


class Resume(BaseModel):
    headline: str
    summary: str
    skills: list[SkillGroup]
    experience: list[Experience]
    projects: list[Project]
    education: list[Education]
    education_notes: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    additional_info: list[str] = Field(default_factory=list)

    def as_text(self) -> str:
        """Plain-text rendering used as LLM context (compact, labelled sections)."""
        out = [f"HEADLINE: {self.headline}", "SUMMARY", self.summary, "SKILL CATEGORIES"]
        out += [f"{g.category}: {', '.join(g.items)}" for g in self.skills]
        out.append("PROFESSIONAL EXPERIENCE")
        for e in self.experience:
            out.append(f"{e.title} | {e.company} | {e.location} | {e.start} - {e.end}")
            out += [f"- {b}" for b in e.bullets]
        out.append("PROJECTS")
        for p in self.projects:
            out.append(f"{p.name} | {p.meta}".rstrip(" |"))
            out += [f"- {b}" for b in p.bullets]
            if p.technologies:
                out.append(f"Technologies: {', '.join(p.technologies)}")
        out.append("EDUCATION")
        out += [f"{d.degree} | {d.institution} | {d.start} - {d.end}" for d in self.education]
        out += self.education_notes
        if self.languages:
            out.append("LANGUAGES")
            out += self.languages
        out.append("ADDITIONAL INFORMATION")
        out += [f"- {a}" for a in self.additional_info]
        return "\n".join(out)


    def evidence_text(self, recent_roles: int = 3) -> str:
        """Shorter view for the cover-letter calls (~600 tokens less than `as_text`).

        Keeps what a letter cites: the latest roles in full, projects, skills and degrees.
        Older roles keep only their header line; the summary is cut to its first sentence.
        """
        out = [f"HEADLINE: {self.headline}", "SUMMARY", self.summary.split(". ")[0].rstrip(".") + "."]
        out.append("SKILL CATEGORIES")
        out += [f"{g.category}: {', '.join(g.items)}" for g in self.skills]
        out.append("PROFESSIONAL EXPERIENCE")
        for i, e in enumerate(self.experience):
            out.append(f"{e.title} | {e.company} | {e.location} | {e.start} - {e.end}")
            if i < recent_roles:
                out += [f"- {b}" for b in e.bullets]
        out.append("PROJECTS")
        for p in self.projects:
            out.append(f"{p.name} | {p.meta}".rstrip(" |"))
            out += [f"- {b}" for b in p.bullets]
            if p.technologies:
                out.append(f"Technologies: {', '.join(p.technologies)}")
        out.append("EDUCATION")
        out += [f"{d.degree} | {d.institution} | {d.start} - {d.end}" for d in self.education]
        return "\n".join(out)


# --------------------------------------------------------------------------- LLM output


class JobAnalysis(BaseModel):
    company: str = ""
    role: str = ""
    industry: str = ""
    # City of the job as stated in the JD ("" if not stated, "Remote" for remote roles).
    location: str = ""
    # What the company does: products, customers, domain. Drives the JD-specific project.
    company_profile: str = ""


class TeamNeed(BaseModel):
    need: str
    evidence: str = ""  # the candidate's closest real work for this need
    gap: str = ""


class ProjectPlan(BaseModel):
    name: str = ""
    problem: str = ""
    approach: str = ""
    covers: list[str] = Field(default_factory=list)


class JobPlan(BaseModel):
    """Step 1: what the job needs and how the candidate's real work maps onto it."""

    analysis: JobAnalysis = Field(default_factory=JobAnalysis)
    candidate_positioning: str = ""
    team_needs: list[TeamNeed] = Field(default_factory=list)
    project: ProjectPlan = Field(default_factory=ProjectPlan)
    jd_keywords: list[str] = Field(default_factory=list)
    requirements_not_covered: list[str] = Field(default_factory=list)

    def brief(self) -> str:
        """Compact JSON for later prompts (no keyword list, to save tokens)."""
        return self.model_dump_json(exclude={"jd_keywords"}, exclude_defaults=True)


class SkillAddition(BaseModel):
    skill: str
    category: str = "Additional"


class ExperiencePointers(BaseModel):
    company: str
    role: str = ""
    bullets: list[str]


class ProjectPointers(BaseModel):
    project: str
    bullets: list[str]


class NewProject(BaseModel):
    name: str
    bullets: list[str]
    technologies: list[str] = Field(default_factory=list)


class ResumeAdditions(BaseModel):
    analysis: JobAnalysis = Field(default_factory=JobAnalysis)
    # Every skill, tool, method and domain term the JD asks for, in the JD's own wording.
    jd_keywords: list[str] = Field(default_factory=list)
    summary_pointers: list[str] = Field(default_factory=list)
    skills_to_add: list[SkillAddition] = Field(default_factory=list)
    experience_pointers: list[ExperiencePointers] = Field(default_factory=list)
    existing_project_pointers: list[ProjectPointers] = Field(default_factory=list)
    new_project: NewProject | None = None
    education_pointers: list[str] = Field(default_factory=list)
    charity_product_pointers: list[str] = Field(default_factory=list)
    requirements_not_covered: list[str] = Field(default_factory=list)
    # The JD's job title as the headline (role titles are never changed).
    headline: str = ""


class MergedSummary(BaseModel):
    summary: str


# --------------------------------------------------------------------------- cover letter


class CoverLetter(BaseModel):
    company: str
    role: str
    greeting: str = "Dear Hiring Team,"
    paragraphs: list[str] = Field(min_length=3, max_length=6)
    closing: str = "Sincerely,"


# --------------------------------------------------------------------------- reflection (HR judge)


class CriterionScore(BaseModel):
    score: int = Field(default=0, ge=0)
    reason: str = ""


class JudgeVerdict(BaseModel):
    """HR / ATS review of a tailored resume against the JD and company profile."""

    tech_stack: CriterionScore = Field(default_factory=CriterionScore)
    experience: CriterionScore = Field(default_factory=CriterionScore)
    company_project: CriterionScore = Field(default_factory=CriterionScore)
    ats_keywords: CriterionScore = Field(default_factory=CriterionScore)
    credibility: CriterionScore = Field(default_factory=CriterionScore)
    decision: str = ""
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list)
