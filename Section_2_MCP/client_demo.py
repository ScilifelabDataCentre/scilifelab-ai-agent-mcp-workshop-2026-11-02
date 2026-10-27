"""Host 1: call the literature-review server without any LLM (MCP Python SDK v2 Client).

    python client_demo.py                                  # default query
    python client_demo.py '"spatial transcriptomics" AND brain'
    MCP_URL=https://<app>.serve.scilifelab.se/mcp python client_demo.py
"""

import asyncio
import os
import sys

from mcp import Client

from litreview import config
from litreview.workshop import is_error, show_papers, text_of


async def main(url: str, query: str) -> None:
    async with Client(url) as client:
        listed = await client.list_tools()
        print("Tools:", ", ".join(tool.name for tool in listed.tools))
        result = await client.call_tool("search_literature", {"query": query, "max_results": 5})
    if is_error(result):
        print("Tool error:", text_of(result))
        return
    data = result.structured_content
    print(f"\n{data['hit_count']} hits | served from {data['served_from']} | query sent: {data['query_sent']}\n")
    show_papers(data["papers"])


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip() or config.DEFAULT_QUERY
    asyncio.run(main(os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp"), query))
