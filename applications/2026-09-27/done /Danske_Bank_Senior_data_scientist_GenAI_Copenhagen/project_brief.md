# Project prep - Conversation Masking and Summarisation Pipeline

Added for: Senior data scientist GenAI at Danske Bank (Copenhagen)
Apply: https://dk.linkedin.com/jobs/view/senior-data-scientist-genai-at-danske-bank-4466553403
Company profile: A Nordic bank whose Personal Customers AI Centre of Excellence builds adviser and customer-facing GenAI solutions for its retail customers.

## On the resume

- Built an NLP pipeline for customer-service chat transcripts that masks personal data with a fine-tuned BERT NER model and summarises multi-turn conversations with an LLM for advisers.
- Evaluated masking with entity-level precision, recall and exact match and summaries with ROUGE and LLM judges for faithfulness, then served the pipeline with FastAPI and Docker, tracking runs in MLflow.

**Technologies:** Hugging Face Transformers, BERT, LangChain, OpenAI API, ROUGE, FastAPI, Docker, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- NLP
- GenAI
- LLMs
- RAG
- vector databases
- embeddings
- transformers
- LangChain
- OpenAI APIs
- Hugging Face
- NER
- summarisation
