# Senior Applied Scientist - AI Platform

- **Company:** Datadog
- **Location:** Paris, Île-de-France, France
- **Opened:** 2026-09-24 10:43 UTC (8h ago)
- **Level:** Senior+
- **Apply:** https://fr.linkedin.com/jobs/view/senior-applied-scientist-ai-platform-at-datadog-4462477905 (LinkedIn)

## Job description

AI Platform builds the foundations of Datadog's AI efforts. The org is 70+ people organised in three pillars: training and serving (GPU clusters, distributed training, low-level infrastructure), agents (agent harnesses, memory systems, the internal AI gateway that routes every LLM request at Datadog), and evaluation and experimentation. This role sits in the evaluation and experimentation pillar, which owns Datadog's shared annotation and evaluation infrastructure — including the evaluation scenario store and the telemetry archival systems used across the Bits org. Together they let an agent travel back in time and query what Datadog looked like at the exact moment an incident happened, so scenarios can be replayed and agent performance tracked over time.

Specifically, you'll be the first applied scientist on GenSim (Generative Simulations), the team that builds the environments Datadog's agents learn in. GenSim doesn't replay sampled telemetry — it stands up real, fully instrumented applications that talk to Datadog, drives them with representative traffic, injects controlled failures, and records what happens. Because GenSim injected the failure, it knows the ground truth. That corpus — hundreds of postmortem-derived scenarios and thousands of runnable applications — is today the primary source of post-training data for Datadog's own SRE model, and the substrate that Bits AI SRE and our other agents are trained and evaluated against.

The team has no applied science support today and is learning post-training data methodology on the fly. That's the gap this role fills, and the open questions are the interesting part. How do you tell whether a generated environment is actually representative of the messy, incomplete telemetry real customers run — rather than a suspiciously clean one where every monitor exists and every service emits complete logs? How do you make injected problems genuinely hard, and how do you even measure difficulty? How do you define and control the quality of post-training data when correctness, representativeness and difficulty pull in different directions? How do you evaluate an agent end to end when the trajectory is non-deterministic? Creating simulated agent environments for monitoring and SRE work is not well solved in open source or in published research, and Datadog is the leading company in this field. If those are the problems you want to spend your time on, come build this with us.

What You'll Do:

- Own the applied science direction for GenSim: set the methodology and the forward-looking technical calls on how simulated environments and post-training data should be built, on a team where that decision-making does not exist yet.

- Define, measure and raise the quality of post-training data — basic correctness, representativeness against the real distribution of customer systems and production telemetry, and difficulty — and make those measures something the team can act on release over release.

- Close the realism gap. Simulated environments today are too clean and the injected problems are not yet hard enough; you'll drive the research and the engineering that make them look like real, imperfect production systems.

- Build scalable, production-grade systems rather than research scripts. The output is not just a dataset — it is a system of synthetic environments that must be reliable and invokable inside a training loop.

- Determine how this data is best applied, in LLM post-training and in evaluation, and own the agent and LLM application evaluation approaches for these environments.

- Work cross-functionally with the engineers and applied scientists on adjacent teams — Bits AI SRE, the model training effort, and the wider evaluation and experimentation pillar — so that what you learn moves freely in both directions.

Who You Are:

- You have a PhD, MS or equivalent research experience in a scientific field, with strong applied mathematics grounding.

- 6+ years of relevant applied science or ML engineering experience, including setting technical direction for others.

- You have hands-on experience with LLM and agent post-training data: how it is created, managed, and how training-data quality is controlled. This is the requirement that matters most.

- You have real domain expertise in LLMs and agentic applications — not classical ML fine-tuning. Fine-tuning classifiers or traditional models is a different problem from the one this team is solving.

- You have evaluated agents or LLM applications, and can define what 'good' means before you measure it.

- You are a strong programmer and production software engineer. Python at minimum, plus the ability to ship scalable production systems and work with distributed systems.

- You collaborate well across engineering and science teams, and you're comfortable being the domain expert who decides what comes next.

- You thrive in ambiguity and can make sound technical calls when the path isn't yet defined.

Bonus Points:

- Hands-on LLM fine-tuning, post-training or model training experience.

- Background in statistics, experiment design and data analysis.

- Experience deploying production-level ML infrastructure.

- Observability or monitoring systems background.

- Architecture-level understanding of LLMs.

Benefits & Growth:

- New hire stock equity (RSUs) and employee stock purchase plan (ESPP)

- Continuous professional development, product training, and career pathing

- Intra-departmental mentor and buddy program for in-house networking

- An inclusive company culture and the ability to join our Community Guilds

- Access to Inclusion Talks, our internal panel discussions

- Free, global Spring Health benefits for employees and dependents age 6+

- Competitive global benefits

Benefits and Growth listed above may vary based on the country of your employment and the nature of your employment with Datadog.

About Datadog: 

Datadog is the leading observability and security platform for the AI era, providing businesses with unified visibility across the technology stack to manage complexity at scale. It brings applications, infrastructure, data, models, and security into one place, using AI to detect and resolve issues before they impact customers. Trusted globally by Fortune 500 companies and high-growth AI leaders, Datadog enables businesses to move faster with clarity and confidence. Learn more about #DatadogLife on Instagram, LinkedIn, and Datadog Learning Center. 

Equal Opportunity at Datadog:

Datadog is proud to offer equal employment opportunity to everyone regardless of race, color, ancestry, religion, sex, national origin, sexual orientation, age, citizenship, marital status, disability, gender identity, veteran status, and other characteristics protected by law. We also consider qualified applicants regardless of criminal histories, consistent with legal requirements. Here are our Candidate Legal Notices for your reference.

Datadog endeavors to make our Careers Page accessible to all users. If you would like to contact us regarding the accessibility of our website or need assistance completing the application process, please complete this form. This form is for accommodation requests only and cannot be used to inquire about the status of applications.

Privacy and AI Guidelines:

Any information you submit to Datadog as part of your application will be processed in accordance with Datadog’s Applicant and Candidate Privacy Notice. For information on our AI policy, please visit Interviewing at Datadog AI Guidelines.
