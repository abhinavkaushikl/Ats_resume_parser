# Project prep - Support Conversation Topic Discovery

Added for: Senior Machine Learning Scientist at Fin (Dublin)
Apply: https://job-boards.greenhouse.io/intercom/jobs/6531495
Company profile: Fin, now part of Salesforce, builds an AI customer service agent that resolves support issues end to end for businesses, alongside the Intercom help desk.

## On the resume

- Built a topic discovery system for customer support conversations, embedding tickets with Sentence-BERT and clustering them with DBSCAN to surface recurring issues an AI agent could not resolve.
- Evaluated cluster quality offline against labelled samples and an LLM judge, compared it with a supervised baseline, then served results through FastAPI with SQL-backed reports.

**Technologies:** Python, Sentence-BERT, DBSCAN, Scikit-learn, PyTorch, SQL, Matplotlib, FastAPI

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- applied machine learning
- ML framing
- exploratory data analysis
- offline evaluation
- experiment design
- prototypes to production
- NLP
- deep learning
- clustering
- transformer neural networks
- SQL
- MSc
