# Project prep - Self-Service Multi-Agent Assistant

Added for: AI engineer for agentic AI at Danske Bank (Copenhagen)
Apply: https://dk.linkedin.com/jobs/view/ai-engineer-for-agentic-ai-at-danske-bank-4466544478
Company profile: A Nordic bank whose Personal Customers AI Centre of Excellence builds conversational AI and self-service assistants for its retail customers.

## On the resume

- Built a multi-agent assistant for retail banking self-service in LangGraph, where a router delegates to specialist agents that call tools through MCP and query a RAG knowledge base.
- Evaluated relevance, faithfulness and hallucination with LLM judges on a regression suite, then deployed on AWS Bedrock behind FastAPI in Docker with structured logging and tracing.

**Technologies:** AWS Bedrock, LangGraph, LangChain, MCP, OpenAI API, FastAPI, Docker, LLM Evals

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- AI agents
- multi-agent
- LangChain
- LangGraph
- AWS Bedrock
- AWS Agent Core
- RAG pipelines
- vector databases
- embedding models
- tool use
- prompt engineering
- LLM evaluation
