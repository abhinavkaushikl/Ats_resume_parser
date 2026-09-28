# Project prep - Support Resolution Prediction Model

Added for: Staff Machine Learning Scientist at Fin (Dublin)
Apply: https://job-boards.greenhouse.io/intercom/jobs/6654793
Company profile: Fin, now part of Salesforce, builds an AI customer service agent that resolves support issues end to end for businesses, alongside the Intercom help desk.

## On the resume

- Built a model predicting whether an AI support agent will resolve a customer conversation, combining transformer embeddings of the conversation with LightGBM to route likely failures to human agents.
- Evaluated it offline on historical conversations with calibration and precision-recall analysis, designed an experiment to measure routing impact, then served it through FastAPI with MLflow.

**Technologies:** PyTorch, Hugging Face Transformers, LightGBM, Scikit-learn, SQL, FastAPI, MLflow, Matplotlib

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- applied ML
- technical leader
- mentoring
- technical standards
- ML framing
- exploratory data analysis
- offline evaluation
- prototypes to production
- NLP
- deep learning
- clustering
- SQL
