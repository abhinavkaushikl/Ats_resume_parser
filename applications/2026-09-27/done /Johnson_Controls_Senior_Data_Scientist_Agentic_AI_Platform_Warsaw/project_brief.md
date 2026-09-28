# Project prep - Building Maintenance Agent Platform

Added for: Senior Data Scientist (Agentic AI Platform) at Johnson Controls (Warsaw)
Apply: https://pl.linkedin.com/jobs/view/senior-data-scientist-agentic-ai-platform-at-johnson-controls-4456591021
Company profile: Johnson Controls provides building systems, thermal management and energy efficiency solutions for data centers, healthcare, manufacturing and other industries.

## On the resume

- Built a multi-agent assistant for building maintenance teams in LangGraph, with a planner calling tools over equipment data and RAG over service manuals using embeddings, pgvector and re-ranking.
- Evaluated task completion and hallucination with LLM-as-judge pipelines and trajectory review, added human-in-the-loop checkpoints, and served it through FastAPI on Azure with MLflow tracking.

**Technologies:** LangGraph, Azure OpenAI, pgvector, FastAPI, MLflow, Databricks, Docker, Python

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- multi-agent systems
- LangGraph
- tool calling
- RAG
- embeddings
- pgvector
- re-ranking
- LLM-as-judge
- hallucination detection
- guardrails
- Azure
- MLflow
