# Project prep - Marketplace Recommendation Ranking Service

Added for: Data Scientist - Machine Learning at Catawiki (Lisbon)
Apply: https://pt.linkedin.com/jobs/view/data-scientist-machine-learning-at-catawiki-4442867866
Company profile: Catawiki is an online marketplace where people buy and sell special objects through weekly auctions curated by in-house experts.

## On the resume

- Built a two-stage recommender for an online marketplace, retrieving candidate items with SBERT embeddings and re-ranking them with a LightGBM model trained on user browsing and bidding events.
- Evaluated ranking quality offline with time-based splits and recall and NDCG metrics, then served real-time and batch predictions through FastAPI on Kubernetes with MLflow model versioning.

**Technologies:** Python, PyTorch, Kubernetes, GCP, SQL, LightGBM, FastAPI, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- production-ready models
- machine learning
- advanced statistics
- Python
- SQL
- real-time predictions
- batch predictions
- Kubernetes
- Google Cloud Platform
- recommender systems
- PyTorch
- CI/CD
