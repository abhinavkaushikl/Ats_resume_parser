# Founding AI Engineer

- **Company:** Alago
- **Location:** Munich, Bavaria, Germany
- **Opened:** 2026-09-24 11:42 UTC (7h ago)
- **Level:** Mid
- **Apply:** https://de.linkedin.com/jobs/view/founding-ai-engineer-at-alago-4469731873 (LinkedIn)

## Job description

The problem

The construction industry loses $1.6 trillion a year to inefficiency, and most of it is avoidable. The knowledge that would prevent it already exists. It's just trapped in PDFs, meeting protocols, and email threads nobody can search. Every new project relearns what the last one already knew.

We're building the opposite of that: software for the people who run large, complex construction projects. It reads the documents, tracks the decisions, and catches the mistakes early. The model isn't the moat. The project memory is, and it compounds: every project makes the system better, and a competitor starting today is already years of projects behind.

Our software runs today on a live autobahn construction program and an S-Bahn transit program: multi-year timelines, hundreds of thousands of pages of specs, protocols, and site communications, and real consequences when we get an answer wrong.

We're pre-seed, led by Realyze Ventures, whose LPs include Zech and other large European construction groups. Co-investors: D11Z, the family office behind Aleph Alpha, and the CDTM Venture Fund, backed by 300+ CDTM alumni including the founders of Personio and Alasco and DeepMind's Technical Director. 25+ live customers.

Tasks

What you'd work on

Two problems, both of which need state-of-the-art answers.

Agent harness engineering for construction documents. One summary doesn't fit all. "Structural risk" means something different in an RFI, a cost review, and a schedule reconciliation. We build multi-agent harnesses (specialized extraction, reasoning, and evaluation stages) that route a 400-page tender document or a protocol archive into the right pipeline with the right context.

Part of that is context compression: what the system should remember, forget, and surface, and at which decision point, when a project runs five years and touches 50 stakeholders. There's no clean top-k answer, so this gets solved in production, not in a library. If you've read what Anthropic and Vercel have written about agent harnesses and thought "yes, that's the hard part of shipping production agents," this is the job.

Project memory as a compounding moat. We started with meeting transcripts. Now we're building a decision graph that grows with every project: not just what was decided, but why, by whom, against which alternatives, and how it played out. That graph feeds the next project. The hard part is reconstructing the "why" when it's buried in a messy German protocol. We want the person who finds that problem interesting.

Stack. TypeScript, Next.js, Vercel, Supabase (Postgres + pgvector), LangChain, Vercel AI SDK, LangFuse, shadcn/ui. Every engineer gets €500/month for AI tooling: Claude Code, Cursor background agents, and whatever frontier model you want to test. No legacy. Greenfield.

How we work

- We ship at 80% and improve in the next iteration. Our users are on live infrastructure projects, so we learn from production.

- We'd rather you read the paper than reach for the nearest library. Most of what we build doesn't have a library yet.

- Feedback is direct and it's about the work. We move too fast to be precious about it.

- High ownership. If you spot the problem, it's yours to fix.

Requirements

Who we're looking for

You reason from user pain to solution to measurable outcome, and you can sit across from a non-technical customer and understand how they actually work.

Since you own things end to end, that includes the frontend. That means being comfortable not only with the AI engineering side, but with TypeScript and React too.

You prototype fast and measure everything. You also care about reliability, because on a live construction project, wrong has consequences.

You're comfortable without a map. Most of these problems don't have answers yet, so you read papers, build prototypes, and compare approaches instead of waiting for a best practice to show up.

Level is open. If you're exceptional, we'll build the scope around you.

Nice to have, not required: serious open-source work, an earlier stint as an early employee at a startup, real depth in document understanding or agent systems, or something you shipped that replaced hours of human labor.

We work in English. German helps for customer calls but isn't required. We have native speakers for that.

Benefits

The offer

You'll be one of our first engineers, which means you own critical parts of the product end to end and work directly with the founders. It's early enough that you help decide how the company works, and the path from here goes to either top individual contributor or VP Engineering, depending on where you're strongest.

Equity: 0.5% to 1.5%, four-year vest, 1.5-year cliff.

Hybrid: three days a week in our central Munich office. If that's a dealbreaker for you, let's talk.

How hiring works

Three stages, no endless loops.

- A 30-minute call with one of our engineers.

- A 30-minute call with Vinzenz, our technical co-founder.

- An onsite case study in Munich. We send the materials ahead (plan on about 4 hours of prep), then we work through it together in the office. This is where we see how you think, debug, and ship under real conditions.

Offer decided within 24 hours of the case study, out within 48.
