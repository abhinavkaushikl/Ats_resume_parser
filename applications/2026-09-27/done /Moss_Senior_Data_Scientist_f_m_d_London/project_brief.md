# Project prep - Invoice Extraction and Anomaly Pipeline

Added for: Senior Data Scientist (f/m/d) at Moss (London)
Apply: https://uk.linkedin.com/jobs/view/senior-data-scientist-f-m-d-at-moss-4466524542
Company profile: Moss is a finance AI platform that automates card issuing, invoice management and expenses for Europe's mid-sized businesses.

## On the resume

- Built an invoice processing pipeline that extracts fields with an LLM into Pydantic structured outputs, classifies spend categories with LightGBM and flags unusual payments with Isolation Forest.
- Evaluated extraction against a hand-labelled gold set with automated tests, robustness checks and cost and latency tracking, then served it through FastAPI with MLflow monitoring.

**Technologies:** Python, OpenAI, Pydantic, LightGBM, Isolation Forest, Scikit-learn, FastAPI, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- LLM app/agent
- tool use/function calling
- RAG
- structured outputs
- guardrails
- extraction
- classification
- anomaly detection
- scikit-learn
- XGBoost/LightGBM
- PyTorch
- evaluation & monitoring
