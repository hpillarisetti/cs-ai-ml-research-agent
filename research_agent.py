"""Evidence-first CS and AI/ML research agent.

The graph plans a focused question, retrieves papers from arXiv through the
MCP server's public-tool logic, synthesizes only from supplied evidence, and
then runs an audit gate before returning a response. The implementation keeps
model output separated from evidence and supports abstention when evidence is
too thin.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from mcp_server import audit_claims, research_scope_check, search_arxiv

load_dotenv()


class ResearchState(TypedDict):
    topic: str
    plan: list[str]
    papers: list[dict[str, Any]]
    draft: str
    claims: list[str]
    audit: dict[str, Any]
    final_report: str
    status: str


def get_llm() -> ChatOpenAI:
    """Create the model client without hard-coding a vendor or secret."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=0,
    )


def plan_node(state: ResearchState) -> dict[str, Any]:
    scope = research_scope_check(state["topic"])
    if not scope["allowed"]:
        return {"plan": [], "status": "blocked", "final_report": scope["guidance"]}
    prompt = (
        "You plan literature research in computer science and AI/ML. Return exactly three "
        "short search queries, one per line. Prefer technical terms and evaluation terms. "
        f"Topic: {state['topic']}"
    )
    response = get_llm().invoke([HumanMessage(content=prompt)]).content
    plan = [line.lstrip("-0123456789. ").strip() for line in response.splitlines() if line.strip()][:3]
    return {"plan": plan, "status": "planned"}


def retrieve_node(state: ResearchState) -> dict[str, Any]:
    papers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in state["plan"]:
        for paper in asyncio.run(search_arxiv(query, max_results=3)):
            if paper["url"] not in seen:
                seen.add(paper["url"])
                papers.append(paper)
    return {"papers": papers[:8], "status": "retrieved"}


def synthesize_node(state: ResearchState) -> dict[str, Any]:
    if not state["papers"]:
        return {
            "draft": "I could not find sufficient literature metadata to answer this responsibly.",
            "claims": [],
            "status": "insufficient_evidence",
        }
    evidence = "\n\n".join(
        f"[{index + 1}] {paper['title']}\nURL: {paper['url']}\nAbstract: {paper['abstract']}"
        for index, paper in enumerate(state["papers"])
    )
    system = """You are a careful CS and AI/ML research assistant. Use only the supplied paper metadata and abstracts. Do not invent benchmark results, implementation details, or causal claims. Write a compact answer with: (1) scope, (2) evidence-backed findings, (3) limitations, and (4) numbered citations like [1]. Then add a final line beginning CLAIMS: with up to three atomic factual claims separated by |."""
    response = get_llm().invoke(
        [SystemMessage(content=system), HumanMessage(content=f"Question: {state['topic']}\n\nEvidence:\n{evidence}")]
    ).content.strip()
    body, _, claim_line = response.partition("CLAIMS:")
    claims = [claim.strip() for claim in claim_line.split("|") if claim.strip()]
    return {"draft": body.strip(), "claims": claims, "status": "synthesized"}


def audit_node(state: ResearchState) -> dict[str, Any]:
    audit = audit_claims(state["claims"], len(state["papers"]))
    if audit["verdict"] == "PASS":
        return {"audit": audit, "final_report": state["draft"], "status": "complete"}
    report = (
        f"{state['draft']}\n\nEvidence note: This draft needs review before reliance. "
        f"Audit verdict: {audit['verdict']}. {audit['note']}"
    )
    return {"audit": audit, "final_report": report, "status": "needs_review"}


def route_after_plan(state: ResearchState) -> str:
    return "retrieve" if state["status"] == "planned" else END


def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("audit", audit_node)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", route_after_plan, {"retrieve": "retrieve", END: END})
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", "audit")
    graph.add_edge("audit", END)
    return graph.compile()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first CS/AI/ML research agent")
    parser.add_argument("topic", help="A focused CS or AI/ML research question")
    parser.add_argument("--json", action="store_true", help="Print full structured state")
    args = parser.parse_args()
    state: ResearchState = {
        "topic": args.topic, "plan": [], "papers": [], "draft": "", "claims": [],
        "audit": {}, "final_report": "", "status": "new",
    }
    result = build_graph().invoke(state)
    print(json.dumps(result, indent=2) if args.json else result["final_report"])


if __name__ == "__main__":
    main()
