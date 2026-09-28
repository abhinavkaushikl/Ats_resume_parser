# Project prep - Business Process Knowledge Graph

Added for: Data Science Expert (Domain Models) - Data Labs at SAP (Munich)
Apply: https://careers.sap.com/job/Garching-bei-München-(Munich)-Data-Science-Expert-(Domain-Models)-Data-Labs-(mfd)-85748/1431659633/
Company profile: SAP builds enterprise business software used across finance, procurement and supply chain, and its Application AI team builds the semantic context layer that grounds SAP's AI agents in business data.

## On the resume

- Built a knowledge graph of business entities and order-to-cash process steps in ArangoDB, linking ERP master data to documents so a LangGraph agent could answer questions grounded in both.
- Evaluated graph-plus-vector retrieval against plain RAG with LLM evaluators on curated question sets, and served the agent through FastAPI in Docker with tracing.

**Technologies:** Python, Knowledge Graph, ArangoDB, Embeddings, pgvector, LangGraph, Databricks, FastAPI

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- enterprise ontologies
- semantic models
- knowledge graphs
- RAG pipelines
- embeddings
- vector databases
- semantic retrieval
- enterprise knowledge grounding
- Python
- SQL
- PyTorch
- scikit-learn
