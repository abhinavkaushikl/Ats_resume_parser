# Project prep - Content Policy Risk Classifier

Added for: Senior Staff Machine Learning Engineer - Content Platform at Spotify (Stockholm)
Apply: https://se.linkedin.com/jobs/view/senior-staff-machine-learning-engineer-content-platform-at-spotify-4407885616
Company profile: Spotify is an audio streaming service, and its Content Platform team builds the ML systems that understand, moderate and route music, podcast and audiobook content for listeners and creators.

## On the resume

- Built a risk-detection system for user-generated podcast transcripts and metadata, fine-tuning a Transformer classifier in PyTorch and routing borderline items to an LLM policy reviewer with explanations.
- Evaluated precision and recall per policy category on human-labelled audits with fairness slices, then served the classifier through FastAPI in Docker with MLflow tracking.

**Technologies:** PyTorch, Hugging Face Transformers, SBERT, LLM Evals, FastAPI, MLflow, Docker, Kubernetes

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- production ML systems
- classification
- moderation
- ranking
- risk detection
- content evaluation
- automated decisioning
- multimodal
- PyTorch
- evaluation
- fairness
- explainability
