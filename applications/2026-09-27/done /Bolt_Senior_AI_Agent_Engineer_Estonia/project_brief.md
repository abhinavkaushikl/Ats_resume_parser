# Project prep - HR Workflow Automation Agent

Added for: Senior AI / Agent Engineer at Bolt (Estonia)
Apply: https://ee.linkedin.com/jobs/view/senior-ai-agent-engineer-at-bolt-4457408717
Company profile: Bolt is a European mobility platform for ride-hailing, food delivery, scooters, e-bikes and car-sharing, used by customers and driver and courier partners across many countries.

## On the resume

- Built a LangGraph agent that automates multi-step HR requests across HRIS and payroll APIs, using typed tool contracts, Pydantic input validation, idempotent retries and human approval gates before writes.
- Evaluated the agent with an LLM-evaluator regression suite and audit-logged tool-call traces, then served it through FastAPI and Docker with an event-driven queue for async actions.

**Technologies:** LangGraph, Claude, FastAPI, Pydantic, Docker, LLM Evals, Agent Tracing, pgvector

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- AI agents
- LLM-powered automation
- tool/function calling
- agent evaluation
- observability
- human-in-the-loop
- event-driven architecture
- retrieval
- embeddings
- vector stores
- re-ranking
- audit trails
