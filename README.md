# CS & AI/ML Evidence Research Agent

An evidence-first research agent for computer science and AI/ML questions. It plans focused technical searches, retrieves arXiv metadata through a small MCP server, synthesizes only from retrieved evidence, and runs a conservative claim-quality gate before returning a report.

## Why this project is different

- Targets computer science, AI, ML, systems, computer vision, NLP, and agent research questions.
- Uses live arXiv metadata instead of simulated generic search results.
- Separates retrieved evidence, model-generated synthesis, and quality checks.
- Requires citation markers and audits claim coverage.
- Blocks clearly unsafe request framing before retrieval.
- Treats a passing audit as a review aid, never as fact verification.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` and, if needed, `OPENAI_MODEL` or `OPENAI_BASE_URL` in `.env`.

```bash
python research_agent.py "How do retrieval rerankers affect grounded answers in RAG systems?"
python research_agent.py --json "What evaluation methods measure agent tool-use reliability?"
```

## Project layout

```text
cs-ai-ml-research-agent/
├── research_agent.py          # LangGraph orchestration and CLI
├── mcp_server.py              # Read-only arXiv retrieval and audit tools
├── mcp_config.json            # Example MCP client configuration
├── requirements.txt           # Runtime dependencies
├── .env.example               # OpenAI-compatible model configuration
└── architecture_summary.html  # Optional print-ready HTML version
```

---

# Architecture Summary

## Purpose

- Provide a focused research assistant for computer science and AI/ML questions.
- Turn a narrow question into a cited literature briefing while making evidence limits visible.
- Prefer an evidence-bound answer or a visible review flag over confident unsupported prose.
- Keep the available tool surface read-only and small enough to audit.

## High-level architecture

```text
+-------------------+     +------------------------+     +---------------------+     +------------------------+
| Research Question | --> | LangGraph Orchestrator | --> | Read-only MCP Tools | --> | Evidence-bound Report |
+-------------------+     +------------------------+     +---------------------+     +------------------------+
```

- **Research question**
  - A focused technical question, such as: “How do rerankers affect grounded RAG answers?”
- **LangGraph orchestrator**
  - Owns state, routing, model calls, evidence packaging, and final status.
- **Read-only MCP tools**
  - Supply arXiv discovery, scope review, and deterministic claim checks.
- **Evidence-bound report**
  - Produces a concise briefing with numbered paper citations, limitations, and either `complete` or `needs_review` status.

> **Boundary:** The agent does not browse arbitrary URLs, run shell commands, write files, or make autonomous external changes. It only retrieves literature metadata and produces text for review.

## Agent architecture and data flow

### LangGraph workflow

```text
+------+     +----------+     +------------+     +-------+
| Plan | --> | Retrieve | --> | Synthesize | --> | Audit |
+------+     +----------+     +------------+     +-------+
```

- **Plan node**
  - Runs a scope check before an LLM call.
  - Asks for exactly three focused literature-search queries.
  - Routes to an immediate stop if the topic is blocked.
- **Retrieve node**
  - Calls `search_arxiv` for each query and deduplicates results by paper URL.
  - Caps retrieval at eight papers so the evidence window remains inspectable.
  - Stores title, authors, date, abstract, URL, and source in graph state.
- **Synthesize node**
  - Receives only the question and retrieved paper metadata or abstracts.
  - Is explicitly prohibited from inventing metrics, implementation details, or causal conclusions.
  - Produces a scope, findings, limitations, numbered citations, and up to three atomic claims.
- **Audit node**
  - Measures simple source-to-claim coverage.
  - Flags absolute or promotional language such as “proves,” “always,” and “best.”
  - Returns a review flag instead of silently deleting a weak conclusion.

### State model

- `topic`
  - The original research question.
- `plan`
  - Bounded technical search queries.
- `papers`
  - Retrieved evidence records.
- `draft` and `claims`
  - Model output held separately for evaluation.
- `audit`, `status`, and `final_report`
  - The decision record and final handoff material.

## Evaluation design

### What the agent evaluates

- **Retrieval adequacy**
  - Did the plan create precise technical queries?
  - Did retrieval return enough distinct papers to support the question?
  - Are papers deduplicated and traceable by URL?
- **Grounded synthesis**
  - Does every major finding cite a retrieved item with a numbered marker?
  - Does the draft limit itself to information visible in supplied metadata and abstracts?
  - Does it acknowledge missing evidence rather than filling gaps from model memory?
- **Claim quality**
  - Are claims atomic enough to review individually?
  - Is source coverage at least `0.70` under the simple claim-to-source heuristic?
  - Does the draft avoid unsupported superlatives and absolute claims?
- **Operational quality**
  - Does the run preserve the plan, sources, claims, audit output, and final status when `--json` is used?
  - Can another researcher reproduce the retrieval strategy from the saved state?

### Suggested evaluation set

- Build 30 to 50 questions across RAG, agents, NLP, computer vision, systems, ML safety, and evaluation.
- For each question, define:
  - Expected query concepts.
  - At least two relevant papers or paper categories.
  - Claims that must be qualified because abstracts alone cannot establish them.
- Track:
  - Citation coverage and citation correctness.
  - Unsupported-claim rate.
  - Abstention or review-flag precision.
  - Latency, token cost, and retrieval-failure rate.

> **Interpretation:** `PASS` means the draft passed a limited coverage and wording check. It does not mean a model, experiment, or paper result has been independently verified.

## Failure cases and safeguards

### Expected failure cases

- **Weak or stale retrieval**
  - An arXiv search may miss peer-reviewed work, return preprints, or surface papers that only share keywords.
- **Abstract overreach**
  - An abstract can describe intent without exposing methods, baselines, caveats, or reproducibility details.
- **Hallucinated synthesis**
  - An LLM can insert plausible-looking benchmark results, citations, or causal explanations absent from the evidence.
- **Evaluation gaming**
  - A response can cite papers often while still making weak connections between a citation and a claim.
- **Tool or network failure**
  - arXiv or the LLM provider can fail, rate-limit requests, or return malformed results.

### Safeguards built into this version

- **Least-privilege tools**
  - The MCP server exposes only public literature retrieval and deterministic review helpers.
- **No arbitrary URL fetch**
  - Prevents prompt-driven access to internal addresses and reduces malicious-content exposure.
- **Evidence boundary**
  - The synthesis prompt receives retrieved evidence and instructs the model to abstain from unknown details.
- **Structured audit**
  - Claims are extracted separately, source coverage is calculated, and risky wording is visible.
- **Review-oriented output**
  - Failed checks result in `needs_review`, not a hidden retry that could mask uncertainty.
- **Scope control**
  - Simple dangerous-topic screening directs the user toward defensive, high-level research framing.
- **Privacy notice**
  - Do not submit proprietary data because public APIs and an LLM provider are involved.

### Recommended next hardening steps

- Add source allowlists for ACL Anthology, OpenReview, Semantic Scholar, and official documentation.
- Add a citation-entailment evaluator that compares each claim with cited passages.
- Cache retrieval by normalized query and timestamp for repeatability.
- Add unit tests for blocked scopes, empty retrieval, citation numbering, and audit routing.
- Require human approval before publishing any report or using results in consequential engineering decisions.

## MCP tools

- `search_arxiv(query, max_results)`
  - Retrieves paper metadata and abstracts from arXiv.
- `audit_claims(claims, source_count)`
  - Flags risky wording and weak source coverage.
- `research_scope_check(topic)`
  - Blocks obviously unsafe research framing.

Run the MCP server by itself with:

```bash
python mcp_server.py
```

## Important limits

- arXiv abstracts are discovery evidence, not a substitute for reading a paper.
- The deterministic audit does not verify scientific truth, reproduce experiments, or certify citations.
- The model is instructed to abstain when retrieval is weak, but every consequential claim still needs human review.
- Public research queries can leave the local machine when arXiv and the configured LLM provider are called.

## Upload to GitHub

Create an empty GitHub repository, then run:

```bash
git add .
git commit -m "Build evidence-first CS AI ML research agent"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/cs-ai-ml-research-agent.git
git push -u origin main
```
