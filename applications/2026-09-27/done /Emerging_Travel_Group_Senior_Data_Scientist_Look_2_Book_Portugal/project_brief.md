# Project prep - Search-to-Booking Conversion Model

Added for: Senior Data Scientist (Look-2-Book) at Emerging Travel Group (Portugal)
Apply: https://www.emergingtravel.com/career/positions/153/
Company profile: Emerging Travel Group is a travel-tech company building online hotel booking platforms and B2B APIs for travel agents, companies and individual travellers.

## On the resume

- Built a model predicting the probability that a hotel search converts into a booking, using LightGBM on price, availability and session features with embedding-based matching of room descriptions.
- Evaluated it offline with ranking metrics and a simulated A/B test on held-out searches, then scheduled training in Airflow and served scores through a FastAPI microservice.

**Technologies:** LightGBM, PySpark, SQL, Airflow, FastAPI, Sentence-BERT, MLflow, Python

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- classic Machine Learning
- Gradient Boosting
- LightGBM
- Classification
- Regression
- Ranking
- Recommendation Systems
- embeddings
- SQL
- PySpark
- Airflow
- Python microservices
