# Senior AI Data Scientist, Agentic Automation (Marketing)

- **Company:** team.blue
- **Location:** Berlin, Berlin, Germany
- **Opened:** 2026-09-05 03:51 UTC (21d ago)
- **Level:** Senior+
- **Apply:** https://de.linkedin.com/jobs/view/senior-ai-data-scientist-agentic-automation-marketing-at-team-blue-4463695987 (LinkedIn)

## Job description

Company Overview

team.blue is the market leader in enabling digital success for small and medium-sized businesses (SMBs) across Europe, catering to over 3 million customers in 25+ languages. Our mission is to make online business success simpler, by providing our customers with all the tools and resources they need to excel online and remain ahead of the curve.

Position Overview

We are looking for a senior data scientist to streamline marketing operations at team.blue, by building agentic systems to run them. You would report into the Applied AI team and work on marketing automation projects.

Marketing here runs across many brands, markets and languages, on a stack that differs brand by brand. The work spans competitive and pricing monitoring, performance reporting and diagnosis, SEO and AI-answer visibility, content refresh, localisation and lifecycle production, paid search and social account hygiene, and tracking and consent QA. Each of these is a multi-step process across several systems, repeated per brand.

The method you will follow matters more than the domain: map processes, quantify the time and resources they consume, determine the ROI impact of agentic automation, build a proof of concept, take it to production and measure the impact of your work. This is closer to building autonomous, business-impact systems than to building pure single purpose models.

What We Are Actually Screening For

Classical ML and applied statistics are the entry fee for this role, necessary and assumed. Everyone we are talking to has them.

Four things separate candidates.

Can you build an agent someone should trust. Most of these agents produce a judgment, backed by numbers: this page lost traffic because of a SERP change, this brand under-converts relative to a comparable one, this competitor’s pricing move matters. A confidently wrong judgment gets read and acted on across several markets before anyone checks it. Lots of this is irreversible, so a recommendation nobody can reconstruct the reasoning for is worse than no recommendation, because it costs trust. Calibration, provenance and auditable workflows are key components of the systems we develop, not a compliance layer on top of them.

Can you tell whether the data underneath is worth reasoning over. These agents read from analytics, search console, ad platforms, CRM and third-party SEO and social tools. Tracking is inconsistent across brands, UTM conventions are followed unevenly, and tags break silently. An agent built on that without checking will generate fluent nonsense at scale. Part of the work is refusing to build on a source until it is trustworthy, and saying so with evidence.

Can you reshape a request. You will be handed requests written by domain experts, and some of them will be the wrong shape: an agent asked to do something a query would do better, or scoped to advise where it could act. We need someone who can understand that, explain better ways to structure the process, and propose a version that works, rather than building what was asked and shipping a thing nobody uses.

Can you take it to production yourself. We mean end to end literally. You write it, you containerise it, you instrument it, and you deploy it with minimal guidance from the devops teams. If the last three things you built were Jupyter notebooks handed to someone else to productionise, this is the wrong role, and no amount of modelling depth compensates.

Your day would involve

- Sitting with an SEO or paid search owner and mapping how a traffic-drop investigation actually runs today across brands, then attaching hours per week to each step of it

- Extracting requirements live from people who do not think in data models

- Designing the state transitions: what triggers, what branches, which APIs get called, where it waits for a human, and what happens when step 4 of 9 fails or a vendor rate-limits you mid-run

- Building the guardrails before the capability: dry-run mode, an approval gate ahead of anything that writes to a live account or publishes externally, least-privilege API scopes, a documented undo

- Deciding where a human stays in the loop, at what confidence threshold, and designing a review queue marketers will open a second time

- Writing evals for output that precision and recall do not capture: is the diagnosis correct, is the cited source real and does it say what the agent claims, does a generated brief hold brand voice in Greek and Dutch as well as in English

- Checking whether the tracking data an agent depends on is sound before building on it, and quantifying the error when it is not

- Wiring an agent to a webhook or a scheduled trigger, and making the handler idempotent so a retry does not double-post a recommendation or apply the same keyword exclusion twice

- Deciding which steps in a flow warrant a frontier model and which run on something cheap, then proving that routing decision with numbers, because these flows run daily across many brands and the bill compounds

- Sitting in a vendor demo asking what their API actually exposes, what the rate limits and quotas are, what their data model looks like, and what integration really costs us

What You Will Bring

- 7+ years building data and ML systems in industry, spanning both sides of the LLM shift. We want the judgment that comes from having debugged systems before you could ask a model what was wrong.

- Somewhere in that history: you have been the only person who did a job end to end. First or only data hire, the single ML person in a small company, or a one-person function inside a large one. We are less interested in company stage than in the condition, because it is what forces someone to map the process, build it, deploy it and answer for it rather than hand each part to a specialist.

- Somewhere in that history: you have shipped something with permission to act on live systems affecting real customers, and you can tell us what you did to sleep at night.

- Expert in Python and ML.

- You ship end to end. Python someone else can still read in six months, a current toolchain (uv, Docker or an equivalent, we care that you re-examine your tooling, not which tool you landed on), your own container, your own instrumentation.

- Production experience with multi-step, tool-calling LLM workflows: orchestration, retries, idempotency, timeouts, partial-failure recovery. State-machine design, not only train/serve pipelines.

- Integration against third-party APIs you do not control. Auth flows, rate limits, pagination, sandbox behaviour that differs from production, and schema changes shipped without notice.

- Cost and latency engineering as a first-class concern: model routing, caching, batching, and the instinct to know what a flow costs per run before Finance asks.

- A safety instinct for systems that take actions: staging modes, approval gates, least-privilege scoping, a way back.

- Evaluation design for generative and agentic output: LLM-as-judge, golden-transcript regression suites, red-teaming. Including calibration: an agent that reports high confidence needs to be right at that rate, and you can show whether it is.

- Process mapping and quantification. You can sit with a domain expert, capture what actually happens rather than what the policy says, and attach hours to it.

- Technical vendor evaluation. Judging a martech vendor on API surface, data model, extensibility and true integration cost, not on the sales deck.

Nice to have

- Master’s or PhD in Computer Science, AI, Machine Learning or a related field

- PromptOps at scale: versioning, testing and rollback of prompts and models as production artefacts

- Prior exposure to martech, ad-tech or SEO tooling and their APIs, or to automation in any domain where output is customer-facing

- Experience evaluating generated output across multiple languages

Right to work

At any stage, please be prepared to provide proof of eligibility to work in the country you are applying for. Unfortunately, we are unable to support relocation packages or sponsor visas.

Come as you are

Everyone is welcome here. Diversity and inclusion are at our core. Far above any technical competence, we value respect, openness, and trusted collaboration. We do not tolerate intolerance.

ESG

At team.blue, our commitment to caring for the environment and each other is at the heart of everything we do. Our latest impact report showcases our ongoing ESG efforts and ambitious sustainability goals. Interested in learning more about our dedication to making a positive impact? Check it out here.

The most trusted digital enabler

team.blue is a leading digital enabler for companies and entrepreneurs. It serves over 3.3 million customers in Europe and has more than 3,000 experts to support them. Its goal is to shape technology and to empower businesses with innovative digital services.

Click here to read more about team.blue
