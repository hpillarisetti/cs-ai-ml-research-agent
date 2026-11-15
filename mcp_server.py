"""Read-only MCP tools for computer-science and AI/ML literature research.

The server intentionally uses public metadata endpoints and does not expose a
shell, filesystem write, or arbitrary URL-fetching tool. This keeps the agent's
tool surface narrow while still giving it citeable paper metadata and abstracts.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cs-ai-ml-research-tools")
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


@mcp.tool()
async def search_arxiv(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search arXiv for CS and AI/ML papers and return citeable metadata.

    Use this for research discovery. Results are metadata and abstracts only;
    the calling agent must not present an abstract as a verified experimental
    result without citing the paper and qualifying the claim.
    """
    max_results = max(1, min(max_results, 10))
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(ARXIV_API, params=params)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    papers: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        paper_id = _clean(entry.findtext("atom:id", default="", namespaces=ARXIV_NS))
        papers.append(
            {
                "title": _clean(entry.findtext("atom:title", default="", namespaces=ARXIV_NS)),
                "authors": [
                    _clean(author.findtext("atom:name", default="", namespaces=ARXIV_NS))
                    for author in entry.findall("atom:author", ARXIV_NS)
                ],
                "published": _clean(entry.findtext("atom:published", default="", namespaces=ARXIV_NS)),
                "abstract": _clean(entry.findtext("atom:summary", default="", namespaces=ARXIV_NS)),
                "url": paper_id,
                "source": "arXiv",
            }
        )
    return papers


@mcp.tool()
def audit_claims(claims: list[str], source_count: int) -> dict[str, Any]:
    """Run conservative, deterministic claim-quality checks.

    This is not fact verification. It flags risky language and insufficient
    source coverage so the orchestrator can request revision or abstain.
    """
    risky_terms = ("always", "never", "proves", "guarantees", "state of the art", "best")
    flagged = []
    for claim in claims:
        terms = [term for term in risky_terms if term in claim.lower()]
        if terms:
            flagged.append({"claim": claim, "risky_terms": terms})
    coverage = min(1.0, source_count / max(1, len(claims)))
    return {
        "claim_count": len(claims),
        "source_count": source_count,
        "source_coverage": round(coverage, 2),
        "flagged_claims": flagged,
        "verdict": "REVISE" if flagged or coverage < 0.7 else "PASS",
        "note": "A PASS is a formatting and coverage check, not proof of truth.",
    }


@mcp.tool()
def research_scope_check(topic: str) -> dict[str, Any]:
    """Reject unsafe or out-of-scope research requests before retrieval."""
    blocked = ("exploit", "malware", "ransomware", "credential theft", "weapon")
    matched = [term for term in blocked if term in topic.lower()]
    return {
        "topic": topic,
        "allowed": not bool(matched),
        "matched_terms": matched,
        "guidance": "Use defensive, high-level research framing." if matched else "Proceed with literature retrieval.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
