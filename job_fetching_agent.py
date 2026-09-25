#!/usr/bin/env python3
"""
job_fetching_agent.py - LangGraph agent that fetches fresh AI / ML / data-science jobs and
saves them as Markdown, using "Job finidng tool.py" as its tool.

Graph
  START -> agent --(tool call?)--> tools -> agent -> ... -> END
  The agent (Groq LLM) turns your request into search settings (hours, locations, seniority),
  calls the fetch_jobs tool, and summarises the result. The tool writes
  jobs/jobs_<timestamp>.md and jobs/latest.md.

Needs in .env: GROQ_API_KEY and/or FALLBACK_LLM_API_KEY + FALLBACK_LLM_MODEL (fallback, OpenAI by default). Search uses free Bing unless SERPER_API_KEY (or GOOGLE_API_KEY + GOOGLE_CSE_ID) is set.

Usage
  .venv/bin/python job_fetching_agent.py
  .venv/bin/python job_fetching_agent.py "senior AI consultant jobs in London and Norway, last 3 days"
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DEFAULT_REQUEST = "Fetch AI / ML / data-science jobs posted in the last 24 hours in all locations."
MAX_JOBS_IN_REPLY = 25   # keeps the tool result small for Groq's tokens-per-minute limit


def _load_finder():
    """Import 'Job finidng tool.py' (its file name has spaces, so a normal import can't)."""
    spec = importlib.util.spec_from_file_location("job_finding_tool", ROOT / "Job finidng tool.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


finder = _load_finder()
LOCATIONS = list(finder.CITIES)

# ==========================================================================
# Tool
# ==========================================================================

@tool
def fetch_jobs(hours: int = 24, cities: list[str] | None = None, senior_only: bool = False) -> str:
    """Search career portals (Greenhouse, Lever, Ashby, SmartRecruiters, Workday, XING, ...) for
    AI / ML / data-science / AI consultant jobs and save them to a Markdown file.

    Args:
        hours: only jobs posted within this many hours (24 = last day, 72 = last 3 days, 168 = last week).
        cities: locations to search; omit to search all of them. Allowed values are listed in the system prompt.
        senior_only: true to keep only senior / lead / staff / principal roles.
    """
    try:
        res = finder.run(hours=hours, cities=cities or None, senior_only=senior_only,
                         out_dir=str(ROOT / "jobs"), extra_companies=str(ROOT / "companies.yaml"))
    except (ValueError, RuntimeError) as ex:
        return f"ERROR: {ex}"

    jobs, new = res["jobs"], res["new_keys"]
    by_city: dict[str, int] = {}
    for j in jobs:
        by_city[j.city] = by_city.get(j.city, 0) + 1
    lines = [f"Saved {len(jobs)} jobs ({len(new)} new) to {res['path']} and {res['latest']}.",
             f"Companies checked: {res['companies_checked']}.",
             "Per location: " + (", ".join(f"{c}: {n}" for c, n in by_city.items()) or "none")]
    newest = sorted(jobs, key=lambda j: (j.key() in new, j.posted.timestamp() if j.posted else 0), reverse=True)
    for j in newest[:MAX_JOBS_IN_REPLY]:
        lines.append(f"- {'NEW ' if j.key() in new else ''}{j.title} | {j.company} | {j.city} | "
                     f"{j.level} | {finder.age(j.posted)} | {j.url}")
    if len(jobs) > MAX_JOBS_IN_REPLY:
        lines.append(f"... and {len(jobs) - MAX_JOBS_IN_REPLY} more in the Markdown file.")
    return "\n".join(lines)


TOOLS = [fetch_jobs]

# ==========================================================================
# Graph
# ==========================================================================

SYSTEM_PROMPT = f"""You are the Job Fetching Agent. You find fresh AI engineering, data science,
machine learning, forward-deployed engineering and AI consultant jobs for the user.

Steps:
1. Read the user's request and work out the search settings:
   - hours: time window (default 24; "3 days" = 72, "a week" = 168).
   - cities: only from this exact list: {", ".join(LOCATIONS)}.
     A city inside Austria/Romania/Norway maps to that country entry; "UK" maps to London.
     Leave cities empty to search everything. If the user asks for a place not on the list, say so.
   - senior_only: true only if the user asks for senior roles.
2. Call fetch_jobs exactly once with those settings. It saves the jobs to a Markdown file.
3. Reply with: the Markdown file path, total and new job count per location, and the 5-10 most
   relevant new jobs (title, company, location, link). If the tool returned an ERROR, explain it
   and what the user should set up. Never invent jobs that the tool did not return."""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_llm():
    """Groq, falling back to the FALLBACK_LLM_* model (OpenAI by default) when Groq fails."""
    llms = []
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEYS", "").split(",")[0].strip()
    if key:
        llms.append(ChatGroq(model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"), api_key=key,
                             temperature=0).bind_tools(TOOLS))
    if fallback_key := os.environ.get("FALLBACK_LLM_API_KEY"):
        from langchain_openai import ChatOpenAI
        llms.append(ChatOpenAI(base_url=os.environ.get("FALLBACK_LLM_BASE_URL", "https://api.openai.com/v1"),
                               model=os.environ.get("FALLBACK_LLM_MODEL", ""), api_key=fallback_key,
                               timeout=float(os.environ.get("FALLBACK_LLM_TIMEOUT_SECONDS", 300))).bind_tools(TOOLS))
    if not llms:
        sys.exit("Set GROQ_API_KEY or FALLBACK_LLM_API_KEY in .env")
    return llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]


def build_graph():
    llm = build_llm()

    def agent(state: AgentState):
        return {"messages": [llm.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])]}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)   # tool call -> "tools", otherwise END
    g.add_edge("tools", "agent")
    return g.compile()


def main():
    request = " ".join(sys.argv[1:]) or DEFAULT_REQUEST
    print(f"Request: {request}\n")
    result = build_graph().invoke({"messages": [HumanMessage(request)]}, {"recursion_limit": 8})
    print("\n" + "=" * 70 + "\n" + result["messages"][-1].content)


if __name__ == "__main__":
    main()
