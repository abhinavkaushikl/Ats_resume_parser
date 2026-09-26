"""Experience variants: fixed, true alternatives to base-resume bullets (resume_variants.json).

A variant swaps or adds experience bullets written by Abhinav, never by an LLM. It is picked from the JD
(e.g. a JD heavy on time series gets the "timeseries" variant), and the same variant is used to score
the JD (job_match.py) and to build the tailored resume (build_resume.py), so the score matches the resume.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .schemas import Resume

VARIANTS_FILE = Path(__file__).resolve().parent.parent / "resume_variants.json"

_TS = re.compile(r"time[- ]series|forecast\w*|demand planning|arima|prophet|lstm|holt[- ]winters|seasonality", re.I)
_LLM = re.compile(r"\bllms?\b|genai|generative ai|gen ai|\brag\b|agentic|agents?\b|langchain|langgraph|prompt", re.I)


def load_variants() -> dict:
    return json.loads(VARIANTS_FILE.read_text(encoding="utf-8")) if VARIANTS_FILE.exists() else {}


def pick_variant(jd: str) -> str | None:
    """'timeseries' when the JD is heavy on time series / forecasting rather than LLMs, else None (base)."""
    if "timeseries" not in load_variants():
        return None
    title = next((l for l in jd.splitlines() if l.startswith("# ")), "")
    ts, llm = len(_TS.findall(jd)), len(_LLM.findall(jd))
    if _TS.search(title) or (ts >= 4 and ts >= 2 * llm):
        return "timeseries"
    return None


def apply_variant(resume: Resume, name: str | None) -> Resume:
    """A copy of the resume with the variant's bullets swapped in / added (unchanged if name is None)."""
    if not name:
        return resume
    spec = load_variants().get(name)
    if not spec:
        raise ValueError(f"Unknown resume variant '{name}' (see {VARIANTS_FILE.name})")
    out = resume.model_copy(deep=True)
    for change in spec.get("experience", []):
        role = next((e for e in out.experience if change["company"].lower() in e.company.lower()
                     and change["title"].lower() in e.title.lower()), None)
        if role is None:
            raise ValueError(f"Variant '{name}': no role '{change['title']}' at '{change['company']}'")
        for prefix, new in change.get("replace", {}).items():
            idx = next((i for i, b in enumerate(role.bullets) if b.startswith(prefix)), None)
            if idx is None:
                raise ValueError(f"Variant '{name}': no bullet starting '{prefix}'")
            role.bullets[idx] = new
        role.bullets += change.get("add", [])
    return out
