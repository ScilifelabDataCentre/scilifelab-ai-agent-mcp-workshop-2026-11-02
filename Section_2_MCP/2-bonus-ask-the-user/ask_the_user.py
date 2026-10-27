"""Multi round-trip requests (MRTR): the server asks the user a question, the client answers and retries.

    python 2-bonus-ask-the-user/ask_the_user.py              # answer the server's question in the terminal
    python 2-bonus-ask-the-user/ask_the_user.py --wire       # show both rounds as raw HTTP, plus a tampered retry

Needs the reference server: python server.py (or MCP_URL pointing at a deployed one).
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import Client  # noqa: E402
from mcp.client import ClientRequestContext  # noqa: E402
from mcp.types import ElicitRequestParams, ElicitResult  # noqa: E402

from litreview import config  # noqa: E402
from litreview import workshop as ws  # noqa: E402


async def ask_in_terminal(context: ClientRequestContext, params: ElicitRequestParams) -> ElicitResult:
    """Registering this callback is how the client declares that it can answer questions."""
    print("\nThe server asks:", params.message)
    answers = ws.prompt_for_schema(ws.requested_schema(params))
    if not answers:
        return ElicitResult(action="decline")
    return ElicitResult(action="accept", content=answers)


async def with_the_sdk(url: str, query: str, question: str) -> None:
    async with Client(url, elicitation_callback=ask_in_terminal) as client:
        result = await client.call_tool("build_evidence_table", {"query": query, "research_question": question})
    if ws.is_error(result):
        print("Tool error:", ws.text_of(result))
    else:
        ws.show_evidence_table(result.structured_content)


def on_the_wire(url: str, query: str, question: str) -> None:
    caps = {"elicitation": {"form": {}}}
    args = {"query": query, "research_question": question}
    status, first = ws.raw_request(url, "tools/call", {"name": "build_evidence_table", "arguments": args},
                                   name="build_evidence_table", capabilities=caps)
    round1 = first.get("result", {})
    print("Round 1: HTTP", status, "| resultType:", round1.get("resultType"))
    print(json.dumps(round1.get("inputRequests"), indent=2))
    if round1.get("resultType") != "input_required":
        print("Unexpected reply:", json.dumps(first)[:600])
        return

    (key,) = round1["inputRequests"].keys()
    answers = {key: {"action": "accept",
                     "content": {"from_year": 2015, "max_papers": 5, "open_access_only": False}}}

    tampered = round1["requestState"][:-6] + "AAAAAA"
    print("\nRetry with a tampered requestState:", ws.error_summary(*ws.raw_request(
        url, "tools/call",
        {"name": "build_evidence_table", "arguments": args, "inputResponses": answers, "requestState": tampered},
        name="build_evidence_table", capabilities=caps)))

    print("Retry without declaring elicitation:", ws.error_summary(*ws.raw_request(
        url, "tools/call", {"name": "build_evidence_table", "arguments": args}, name="build_evidence_table")))

    status, second = ws.raw_request(
        url, "tools/call",
        {"name": "build_evidence_table", "arguments": args, "inputResponses": answers,
         "requestState": round1["requestState"]},
        name="build_evidence_table", capabilities=caps)
    round2 = second.get("result", {})
    print("\nRound 2: HTTP", status, "| resultType:", round2.get("resultType"))
    if round2.get("structuredContent"):
        ws.show_evidence_table(round2["structuredContent"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wire", action="store_true", help="show the two rounds as raw HTTP")
    parser.add_argument("--query", default="", help="Europe PMC query (empty means the default)")
    parser.add_argument("--question", default="", help="research question (empty means the default)")
    args = parser.parse_args()
    url = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
    query = args.query.strip() or config.DEFAULT_QUERY
    question = args.question.strip() or config.DEFAULT_QUESTION
    if args.wire:
        on_the_wire(url, query, question)
    else:
        asyncio.run(with_the_sdk(url, query, question))


if __name__ == "__main__":
    main()
