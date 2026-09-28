# Project prep - Support Refund Decision Agent

Added for: Applied AI Engineer, Operations Automation at Bolt (Tallinn)
Apply: https://bolt.eu/en/careers/positions/815e1eb0-51f6-4ba1-af7d-5371dcdffe2e/
Company profile: Bolt is a European mobility platform for ride-hailing, delivery and rentals, automating operational decisions such as support, document checks and fraud review.

## On the resume

- Built an LLM agent that decided customer support refund cases for a mobility marketplace, calling order-history and policy tools, with a LightGBM model handling routine cases more cheaply.
- Evaluated it on test sets built from past human decisions, calibrated an LLM judge against human labels, and served it through FastAPI behind an A/B-tested rollout gate.

**Technologies:** Claude, Python, SQL, LangGraph, LLM Evals, LightGBM, FastAPI, Docker

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- LLM systems
- evaluation suite
- agent traces
- LLM judge
- human labels
- A/B test
- fine-tuning
- classic ML
- SQL
- operations automation
- customer support
- document verification
