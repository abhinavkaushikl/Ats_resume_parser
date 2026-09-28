# Project prep - Security Alert Triage Pipeline

Added for: Cybersecurity Data Scientist, Assistant Vice President at State Street (Ireland)
Apply: https://ie.linkedin.com/jobs/view/cybersecurity-data-scientist-assistant-vice-president-at-state-street-4465834206
Company profile: State Street is a global custodian bank and asset manager providing investment servicing, data and analytics to institutional clients.

## On the resume

- Built an alert triage pipeline for security operations that clusters related alerts with Sentence-BERT embeddings and scores their risk with LightGBM on asset and identity features.
- Evaluated triage quality against analyst-labelled incidents, used an LLM to summarise each alert cluster, and ran the pipeline on Databricks with PySpark feeding Power BI dashboards.

**Technologies:** Python, PySpark, Databricks, SQL, Power BI, Sentence-BERT, LightGBM

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- Python
- SQL
- PySpark
- Databricks
- Power BI
- anomaly detection
- graph analytics
- NLP
- GenAI
- SIEM/SOAR
- threat detection
- alert enrichment
