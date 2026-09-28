# Project prep - Marketplace Ad Relevance Ranking

Added for: Senior Machine Learning Engineer I, Search Ads at Etsy (Dublin)
Apply: https://careers.etsy.com/jobs/senior-machine-learning-engineer-i-search-ads-dublin-ireland
Company profile: Etsy is a global online marketplace connecting buyers with independent sellers of handmade, vintage and creative goods, and its Search Ads team builds ML for sponsored search.

## On the resume

- Built a two-stage ad retrieval and ranking system for sponsored search on an online marketplace, pairing Sentence-BERT embedding retrieval with a LightGBM click model and cross-encoder re-ranking.
- Evaluated ranking quality offline with NDCG and simulated A/B comparisons against a baseline, then served the models behind a FastAPI service with MLflow tracking and monitoring.

**Technologies:** PyTorch, LightGBM, Sentence-BERT, Hugging Face Transformers, PySpark, FastAPI, MLflow, Docker

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- machine learning
- information retrieval
- search
- recommendations
- ranking
- natural language processing
- deep learning
- production machine learning systems
- A/B experiments
- retrieval
- user engagement modeling
- testable code
