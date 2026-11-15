# CS & AI/ML Evidence Research Agent

An evidence-first research agent for computer science and AI/ML questions. It is a rebuilt version of the linked starter project, focused on research literature rather than generic web facts.

The agent plans focused technical searches, retrieves arXiv metadata through a small MCP server, synthesizes only from retrieved abstracts, and runs a conservative claim-quality gate before returning a report.

## Why this project is different

- Targets CS, AI, ML, systems, vision, NLP, and agent research questions.
- Uses live arXiv metadata instead of simulated search results.
- Keeps evidence separate from model-generated prose.
- Requires citation markers in the draft and audits claim coverage.
- Blocks clearly unsafe request framing before retrieval.
- Treats a passing audit as a review aid, never as fact verification.

## Architecture

```text
question -> planner -> arXiv retrieval -> evidence-bound synthesis -> claim audit -> report / review flag
```

For a technically detailed, print-ready four-page explanation, open [architecture_summary.html](architecture_summary.html) in a browser.

## Project layout

```text
cs-ai-ml-research-agent/
├── research_agent.py          # LangGraph orchestration and CLI
├── mcp_server.py              # Read-only arXiv retrieval and audit tools
├── mcp_config.json            # Example MCP client configuration
├── requirements.txt           # Runtime dependencies
├── .env.example               # OpenAI-compatible model configuration
└── architecture_summary.html  # Four-page architecture brief
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` and, if needed, `OPENAI_MODEL` or `OPENAI_BASE_URL` in `.env`. The agent accepts an OpenAI-compatible chat endpoint through the `langchain-openai` client.

## Run a research question

```bash
python research_agent.py "How do retrieval rerankers affect grounded answers in RAG systems?"
```

Use `--json` to inspect the plan, retrieved papers, atomic claims, and audit result:

```bash
python research_agent.py --json "What evaluation methods measure agent tool-use reliability?"
```

## Run the MCP server by itself

```bash
python mcp_server.py
```

The server exposes these read-only tools:

- `search_arxiv(query, max_results)`: retrieves paper metadata and abstracts from arXiv.
- `audit_claims(claims, source_count)`: flags risky wording and weak source coverage.
- `research_scope_check(topic)`: blocks obviously unsafe research framing.

## Important limits

- arXiv abstracts are discovery evidence, not a substitute for reading a paper.
- The deterministic audit does not verify scientific truth, reproduce experiments, or certify citations.
- The model is instructed to abstain when retrieval is weak, but every consequential claim still needs human review.
- Public research queries can leave the local machine when the arXiv endpoint and configured LLM provider are called. Do not submit proprietary or sensitive material.

## GitHub upload

Create an empty GitHub repository, then from this folder run:

```bash
git add .
git commit -m "Build evidence-first CS AI ML research agent"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/cs-ai-ml-research-agent.git
git push -u origin main
```
