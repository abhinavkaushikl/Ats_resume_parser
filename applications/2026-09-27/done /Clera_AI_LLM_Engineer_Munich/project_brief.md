# Project prep - Order Document Processing Agent

Added for: AI/LLM Engineer at Clera (Munich)
Apply: https://de.linkedin.com/jobs/view/ai-llm-engineer-at-clera-4471107882
Company profile: Clera builds a B2B SaaS platform that automates quoting and order processing for distributors and manufacturers.

## On the resume

- Built an AI agent that turns unstructured purchase requests and order emails into structured quotes, matching line items to a product catalog with embeddings and a fine-tuned reranker.
- Evaluated extraction and product-match quality against human-labelled orders, and served the agent through a FastAPI backend in Docker on Kubernetes with Terraform-managed infrastructure.

**Technologies:** Python, LangGraph, Embeddings, Cross-Encoder, FastAPI, Docker, Kubernetes, Terraform

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- AI agents
- embeddings
- fine-tune LLMs
- classification and reranking
- product search relevance
- RLHF
- DPO
- data pipelines
- unstructured data
- NLP
- Docker
- Kubernetes
