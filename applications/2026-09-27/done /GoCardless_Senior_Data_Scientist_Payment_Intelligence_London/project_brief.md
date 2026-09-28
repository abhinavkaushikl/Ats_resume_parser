# Project prep - Payment Fraud Sequence Model

Added for: Senior Data Scientist, Payment Intelligence at GoCardless (London)
Apply: https://job-boards.greenhouse.io/gocardless/jobs/7526068
Company profile: A bank payments company that helps businesses collect and send Direct Debit, real-time and open banking payments, with ML to improve payment success and prevent fraud.

## On the resume

- Built a payment fraud detection model that learns from each payer's transaction sequence with an LSTM, combined with LightGBM on engineered account features to flag suspicious debits.
- Validated with time-based splits, precision-recall analysis and a simulated A/B rollout, then served scores through FastAPI on GCP Vertex AI with drift monitoring in MLflow.

**Technologies:** Python, SQL, BigQuery, Vertex AI, PyTorch, LSTM, LightGBM, MLflow

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- fraud prevention
- end-to-end model delivery
- feature engineering
- A/B testing
- monitoring
- deep learning
- sequence-based models
- graph-based models
- Python
- SQL
- BigQuery
- Google Cloud Platform
