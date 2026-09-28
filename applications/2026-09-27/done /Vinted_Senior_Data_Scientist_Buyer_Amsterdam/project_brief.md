# Project prep - Marketplace Search Ranking System

Added for: Senior Data Scientist, Buyer at Vinted (Amsterdam)
Apply: https://careers.vinted.com/jobs/j/4923336101
Company profile: Vinted runs a leading European marketplace for second-hand fashion, connecting millions of members who buy and sell pre-loved items across 20+ markets.

## On the resume

- Built a multi-stage search ranking system for a peer-to-peer resale catalog of unique listings, pairing SBERT dense retrieval with a LightGBM learning-to-rank model and cross-encoder reranker.
- Evaluated ranking quality offline with NDCG and recall on held-out search sessions, then served the ranker through FastAPI over Elasticsearch retrieval, tracked in MLflow.

**Technologies:** Python, LightGBM, PyTorch, SBERT, Elasticsearch, SQL, FastAPI, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- retrieval
- ranking
- personalization
- gradient boosting
- two-tower
- sequence models
- neural rerankers
- Learning-to-Rank
- semantic search
- Python
- SQL
- offline evaluation
