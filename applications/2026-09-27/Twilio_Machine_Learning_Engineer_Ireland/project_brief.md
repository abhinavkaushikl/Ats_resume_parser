# Project prep - Conversation Intent and Summary Pipeline

Added for: Machine Learning Engineer at Twilio (Ireland)
Apply: https://ie.linkedin.com/jobs/view/machine-learning-engineer-at-twilio-4431752760
Company profile: Twilio is a cloud communications platform that helps businesses and developers build personalised customer conversations over voice and messaging.

## On the resume

- Built a conversation analytics pipeline that extracted intents, topics and summaries from customer chat and call transcripts using a fine-tuned BERT classifier and an LLM summarizer.
- Evaluated outputs against labelled test sets and LLM evaluators, tracked experiments in MLflow, and served the models through FastAPI in Docker with latency and quality metrics logged.

**Technologies:** PyTorch, Hugging Face Transformers, MLflow, FastAPI, Docker, GCP, LLM Evals

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- Python
- PyTorch
- Hugging Face Transformers
- NLP
- LLMs
- end-to-end ML pipelines
- model versioning
- experiment tracking
- production inference
- monitoring
- LangGraph
- LLM fine-tuning
