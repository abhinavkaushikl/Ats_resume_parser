# Project prep - Long-Form Media Insight Pipeline

Added for: AI Solutions Architect at Sycomp (Ireland)
Apply: https://ie.linkedin.com/jobs/view/ai-solutions-architect-at-sycomp-4467843765
Company profile: Sycomp is a global IT services and logistics provider delivering cloud, data center, endpoint and security projects for enterprise customers.

## On the resume

- Built a pipeline that extracts structured insight from long recorded meetings, transcribing audio, chunking transcripts with overlap and sending each chunk to Claude on AWS Bedrock with schema-enforced outputs.
- Evaluated extractions against hand-labelled samples with LLM evaluators, added retries on malformed responses, and orchestrated the steps with Step Functions and Lambda, storing results in S3 and OpenSearch.

**Technologies:** AWS Bedrock, Step Functions, Lambda, S3, OpenSearch, Python, Pydantic, LangGraph

## Prepare before the interview

- Sketch the architecture end to end: data in, model / retrieval, evaluation, serving.
- For each technology above: why it was the right choice and one alternative you considered.
- How you evaluated it (offline metrics, test set) and how you would monitor it in production.
- One hard problem and how you solved it; one thing you would do differently.
- Ideally build a small working version and put it on GitHub before the interview.

## JD needs this project speaks to

- AI pipelines
- agentic systems
- AWS Bedrock
- Lambda
- Step Functions
- SageMaker
- OpenSearch
- chunking
- context window management
- structured outputs
- LangGraph
- evaluation pipelines
