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
        out.append("ADDITIONAL INFORMATION")
        out += [f"- {a}" for a in self.additional_info]
        return "\n".join(out)


# --------------------------------------------------------------------------- LLM output


class JobAnalysis(BaseModel):
    company: str = "Company"
    role: str = ""
    industry: str = ""


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
    summary_pointers: list[str] = Field(default_factory=list)
    skills_to_add: list[SkillAddition] = Field(default_factory=list)
    experience_pointers: list[ExperiencePointers] = Field(default_factory=list)
    existing_project_pointers: list[ProjectPointers] = Field(default_factory=list)
    new_project: NewProject | None = None
    education_pointers: list[str] = Field(default_factory=list)
    charity_product_pointers: list[str] = Field(default_factory=list)
    keywords_covered: list[str] = Field(default_factory=list)
    requirements_not_covered: list[str] = Field(default_factory=list)


class MergedSummary(BaseModel):
    summary: str


# --------------------------------------------------------------------------- cover letter


class CoverLetter(BaseModel):
    company: str
    role: str
    greeting: str = "Dear Hiring Team,"
    paragraphs: list[str] = Field(min_length=3, max_length=6)
    closing: str = "Sincerely,"


class UnsupportedClaim(BaseModel):
    claim: str
    reason: str


class FactCheck(BaseModel):
    issues: list[UnsupportedClaim] = Field(default_factory=list)


class Replacement(BaseModel):
    find: str
    replace: str


class Patch(BaseModel):
    replacements: list[Replacement] = Field(default_factory=list)
