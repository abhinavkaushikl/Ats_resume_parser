# Project prep - Sequential Player Skill Model

Added for: Sr Applied Scientist at 2K (Dublin)
Apply: https://job-boards.greenhouse.io/2k/jobs/7784351003?ref=manaboard
Company profile: 2K is a video game publisher behind franchises such as NBA 2K, whose Applied AI team builds matchmaking, skill rating, personalisation and fraud models for players.

## On the resume

- Built an LSTM sequence model in PyTorch that learned player skill embeddings from match event histories, using contrastive training on paired outcomes to support fairer matchmaking and skill rating.
- Evaluated the embeddings on held-out match outcome prediction against an Elo baseline, tracked experiments in MLflow, and served skill scores through a FastAPI service in Docker.

**Technologies:** PyTorch, Python, SQL, Apache Spark, LSTM, MLflow, FastAPI, Docker

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- machine learning
- deep learning
- representation learning
- embedding models
- recommender systems
- ranking systems
- sequence models
- Python
- SQL
- Apache Spark
- PyTorch
- production ML
