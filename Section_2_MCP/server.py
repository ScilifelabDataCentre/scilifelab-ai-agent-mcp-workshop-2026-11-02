"""Literature-review MCP server for the SciLifeLab hands-on workshop.

MCP Python SDK v2 (MCPServer), protocol revision 2026-07-28. The tools search Europe PMC,
which covers PubMed, PubMed Central and preprints, so the server is useful across the life
sciences. It answers 2026-era clients natively and older clients through the SDK's fallback.

Run it:
    python server.py                            Streamable HTTP on http://127.0.0.1:8000/mcp
    python server.py --host 0.0.0.0             inside a container (reachable from outside)
    python server.py --transport stdio          for hosts that start servers as subprocesses
    uv run mcp dev server.py                    MCP Inspector (set Protocol Era to Modern)
"""

import argparse
import asyncio
import json
import os
from typing import Annotated, Literal

from mcp.server.mcpserver import Elicit, MCPServer, RequestStateSecurity, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from litreview import config, europepmc
from litreview.evidence import evidence_rows
from litreview.models import (
    CitingPapers,
    EvidenceRow,
    EvidenceTable,
    PaperLookup,
    ReviewScope,
    SearchResult,
)
from litreview.texts import QUERY_SYNTAX_GUIDE, REVIEW_PROMPT, SERVER_INSTRUCTIONS


def _server_options() -> dict:
    # MRTR round trips carry a signed requestState. Without a shared key the SDK signs with a
    # random per-process key: fine for one process, wrong for several replicas or restarts.
    key = os.environ.get("MCP_STATE_KEY")
    return {"request_state_security": RequestStateSecurity(keys=[key])} if key else {}


mcp = MCPServer(
    "literature-review",
    version="1.0.0",
    instructions=SERVER_INSTRUCTIONS,
    **_server_options(),
)


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def service_root(_request: Request) -> Response:
    """A small public index; MCP clients should use /mcp."""
    return JSONResponse({
        "service": "literature-review",
        "status": "ok",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
    })


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def service_health(_request: Request) -> Response:
    """Unauthenticated liveness endpoint for container and Serve checks."""
    return JSONResponse({"status": "ok"})


def _tool_error(exc: europepmc.LiteratureError) -> ToolError:
    """A tool error the model can explain, instead of a broken connection."""
    hint = ""
    if isinstance(exc, europepmc.UpstreamError):
        hint = " This is a failed search, not evidence that no papers exist."
    return ToolError(f"{exc.kind}: {exc}.{hint}")


# ---------------------------------------------------------------------------
# Tools: model-controlled actions
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_literature(
    query: str = config.DEFAULT_QUERY,
    max_results: int = 10,
    sort: Literal["relevance", "cited", "newest"] = "relevance",
    from_year: int | None = None,
    to_year: int | None = None,
    open_access_only: bool = False,
) -> SearchResult:
    """Search the life-science literature in Europe PMC (PubMed, PubMed Central, preprints).

    query: Europe PMC syntax, for example '"gut microbiome" AND (depression OR anxiety)'.
           Leave it empty to search the workshop's default topic.
    sort: "relevance", "cited" (most cited first) or "newest".
    Returns identifiers, citation counts and a shortened abstract for each paper.
    A "no_results" status is a real answer; an upstream_error is not evidence of absence.
    """
    try:
        data = await asyncio.to_thread(
            europepmc.search, query, max_results=max_results, sort=sort,
            from_year=from_year, to_year=to_year, open_access_only=open_access_only,
        )
    except europepmc.LiteratureError as exc:
        raise _tool_error(exc) from exc
    return SearchResult.model_validate(data)


@mcp.tool()
async def get_paper(paper_id: str) -> PaperLookup:
    """Get one paper's full record: abstract, keywords, MeSH terms and full-text links.

    paper_id: a PMID (12345678), PMCID (PMC1234567), preprint id (PPR123456), DOI (10.xxxx/...),
              or an id from search results such as MED:12345678.
    """
    try:
        data = await asyncio.to_thread(europepmc.get_paper, paper_id)
    except europepmc.LiteratureError as exc:
        raise _tool_error(exc) from exc
    return PaperLookup.model_validate(data)


@mcp.tool()
async def find_citing_papers(paper_id: str, max_results: int = 10) -> CitingPapers:
    """Find papers that cite a given paper: forward citation chasing for a literature review.

    paper_id: a PMID, PMCID, preprint id, DOI, or an id from search results such as MED:12345678.
    """
    try:
        data = await asyncio.to_thread(europepmc.citing_papers, paper_id, max_results=max_results)
    except europepmc.LiteratureError as exc:
        raise _tool_error(exc) from exc
    return CitingPapers.model_validate(data)


# This tool asks the user a question before it runs (elicitation through MRTR). The resolved
# `scope` parameter is hidden from the tool schema; the SDK fills it from the user's answer.
# Clients that do not declare elicitation support get error -32021 for this tool only.

async def ask_review_scope(research_question: str = config.DEFAULT_QUESTION) -> Elicit[ReviewScope]:
    return Elicit(
        f'Build an evidence table for: "{research_question}". '
        "Confirm the scope (the defaults are fine).",
        ReviewScope,
    )


@mcp.tool()
async def build_evidence_table(
    scope: Annotated[ReviewScope, Resolve(ask_review_scope)],
    query: str = config.DEFAULT_QUERY,
    research_question: str = config.DEFAULT_QUESTION,
) -> EvidenceTable:
    """Build a numbered evidence table (most cited first) for a research question.

    Asks the user to confirm the scope first, so it needs a client that supports elicitation.
    """
    max_papers = max(3, min(int(scope.max_papers), config.MAX_RESULTS_LIMIT))
    try:
        data = await asyncio.to_thread(
            europepmc.search, query, max_results=max_papers, sort="cited",
            from_year=scope.from_year, open_access_only=scope.open_access_only,
        )
    except europepmc.LiteratureError as exc:
        raise _tool_error(exc) from exc
    return EvidenceTable(
        research_question=(research_question or "").strip() or config.DEFAULT_QUESTION,
        query_sent=data["query_sent"],
        scope=ReviewScope(from_year=scope.from_year, max_papers=max_papers,
                          open_access_only=scope.open_access_only),
        hit_count=data["hit_count"],
        rows=[EvidenceRow(**row) for row in evidence_rows(data["papers"])],
        source=data["source"],
        retrieved_at=data["retrieved_at"],
        served_from=data["served_from"],
    )


# ---------------------------------------------------------------------------
# Resources: application-provided context
# ---------------------------------------------------------------------------

@mcp.resource("litreview://guide/query-syntax")
def query_syntax_guide() -> str:
    """How to write Europe PMC queries for a literature review."""
    return QUERY_SYNTAX_GUIDE


@mcp.resource("litreview://defaults")
def workshop_defaults() -> str:
    """The default research question and query, used when you do not provide your own."""
    return json.dumps(
        {"default_question": config.DEFAULT_QUESTION, "default_query": config.DEFAULT_QUERY,
         "mode": config.MODE, "max_results_limit": config.MAX_RESULTS_LIMIT},
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompts: user-chosen templates
# ---------------------------------------------------------------------------

@mcp.prompt()
def literature_review(research_question: str = config.DEFAULT_QUESTION) -> str:
    """A step-by-step literature-review workflow that uses this server's tools."""
    return REVIEW_PROMPT.format(question=(research_question or "").strip() or config.DEFAULT_QUESTION)


def main() -> None:
    parser = argparse.ArgumentParser(description="Literature-review MCP server (protocol 2026-07-28)")
    parser.add_argument("--transport", choices=("streamable-http", "stdio"),
                        default=os.environ.get("MCP_TRANSPORT", "streamable-http"))
    parser.add_argument("--host", default=os.environ.get("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "8000")))
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()  # stdio: never print to stdout here, it carries the protocol
        return
    print(f"literature-review MCP server on http://{args.host}:{args.port}/mcp "
          f"(Europe PMC mode: {config.MODE})", flush=True)
    # json_response: plain JSON replies, easy to read with curl.
    # stateless_http: no protocol sessions for older clients either, so any replica can answer.
    mcp.run(transport="streamable-http", host=args.host, port=args.port,
            json_response=True, stateless_http=True)


if __name__ == "__main__":
    main()
