# Project prep - Marketplace Recommendation Ranking Service

Added for: Senior Data Scientist - Machine Learning at Catawiki (Lisbon)
Apply: https://pt.linkedin.com/jobs/view/senior-data-scientist-machine-learning-at-catawiki-4442855950
Company profile: Catawiki is an online marketplace where people buy and sell special objects through weekly auctions curated by in-house experts.

## On the resume

- Built a two-stage recommender for an online marketplace, retrieving candidate items with SBERT embeddings and re-ranking them with a LightGBM model trained on user browsing and bidding events.
- Evaluated ranking quality offline with recall and NDCG, sized the embedding model for serving latency, and ran real-time and batch predictions through FastAPI on Kubernetes with Airflow.

**Technologies:** PyTorch, Docker, Kubernetes, Spark, Airflow, SQL, LightGBM, FastAPI

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- production-ready models
- range of ML techniques
- deployment constraints of large models
- real-time predictions
- Python
- SQL
- PyTorch
- LightFM
- Docker
- Kubernetes
- Google BigQuery
- Spark
