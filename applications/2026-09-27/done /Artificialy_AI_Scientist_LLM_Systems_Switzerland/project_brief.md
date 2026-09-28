# Project prep - Financial Document Question Answering

Added for: AI Scientist - LLM Systems at Artificialy (Switzerland)
Apply: https://ch.linkedin.com/jobs/view/ai-scientist-llm-systems-at-artificialy-4468574508
Company profile: Artificialy is a Swiss AI company in Lugano and Zurich that designs and delivers transparent, tailored AI solutions, including LLM systems for clients in the financial sector.

## On the resume

- Built a retrieval-augmented assistant answering questions over regulatory and financial reports, pairing dense retrieval with a fine-tuned cross-encoder re-ranker and GPT-4 for cited answers.
- Designed the evaluation with a hand-labelled benchmark, LLM-as-judge scoring for faithfulness and error analysis of failed answers, then served the assistant through FastAPI on Azure.

**Technologies:** Python, PyTorch, Scikit-learn, Hugging Face Transformers, OpenAI, LangGraph, FastAPI, Azure

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- LLM-based systems
- retrieval-augmented generation
- agentic systems
- fine-tuning
- LLM-as-judge
- benchmarks
- error analysis
- evaluation methodology
- Python
- SQL
- PyTorch
- Scikit-learn
