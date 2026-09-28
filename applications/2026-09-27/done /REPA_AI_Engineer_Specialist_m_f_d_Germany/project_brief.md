# Project prep - Spare Parts Identification Assistant

Added for: AI Engineer / Specialist at REPA (Bergkirchen)
Apply: https://jobs.smartrecruiters.com/REPAGROUP/744000144725420-ai-engineer-specialist-m-f-d-
Company profile: REPA is a European distributor of spare parts for commercial kitchens, catering equipment and refrigeration, serving service technicians and businesses from warehouses across Europe.

## On the resume

- Built a RAG assistant that matches free-text descriptions of faulty equipment to the right spare part numbers, combining semantic search over catalogues and manuals with Azure OpenAI reasoning.
- Evaluated part-match accuracy with LLM evaluators on historical service requests, logged prompts and outputs without personal data, and exposed it through a FastAPI service on Azure.

**Technologies:** Python, Azure OpenAI, RAG, LangGraph, pgvector, SQL, FastAPI, Docker

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- generative AI applications
- AI agents
- RAG
- LLMs
- prompt engineering
- Python
- SQL
- APIs
- Microsoft Azure
- Azure OpenAI
- proof of concept to production
- Git
