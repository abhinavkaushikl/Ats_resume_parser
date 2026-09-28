# Project prep - Cold-Start Listing Ranker

Added for: Senior Data Scientist - Rankings & Recommendations at Holidu (Munich)
Apply: https://de.linkedin.com/jobs/view/senior-data-scientist-rankings-recommendations-all-genders-at-holidu-4471898984
Company profile: A vacation rental technology company whose search ranking and recommendation systems decide which holiday homes guests discover first.

## On the resume

- Built a two-stage ranking system for a travel marketplace, blending LightGBM learning-to-rank on behavioural signals with SBERT listing embeddings so new listings ranked well before any interactions.
- Evaluated with NDCG on offline replays and a simulated A/B test, then scheduled retraining in Airflow and tracked drift and online/offline agreement in MLflow.

**Technologies:** Python, SQL, LightGBM, XGBoost, SBERT, Airflow, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- ranking models
- recommender systems
- personalization
- cold-start
- re-ranking
- A/B tests
- XGBoost
- LightGBM
- tabular data
- Python
- SQL
- Airflow
