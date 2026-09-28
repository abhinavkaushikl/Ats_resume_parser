# Project prep - Credit Policy RAG Assistant

Added for: Risk AI Data Scientist at ING Nederland (Amsterdam)
Apply: https://ing.talent-community.com/projects/risk-ai-data-scientist/71075
Company profile: ING is a Dutch bank whose Integrated Risk team builds risk identification and credit risk model capabilities used across the group.

## On the resume

- Built a RAG assistant over credit policy documents and banking regulations, combining OCR extraction of PDFs, dense retrieval and a fine-tuned cross-encoder re-ranker to answer risk managers' questions.
- Evaluated answers for hallucination, retrieval quality and drift with LLM evaluators and gold question sets, then served it through FastAPI with MLflow tracking on GCP.

**Technologies:** Python, Hugging Face Transformers, PyTorch, LangGraph, RAG, Vector DB, GCP, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- RAG
- LLMs
- NLP
- agentic workflows
- LangChain/LangGraph
- fine-tuning
- Hugging Face
- PyTorch
- unstructured data
- OCR
- hallucinations
- Python
