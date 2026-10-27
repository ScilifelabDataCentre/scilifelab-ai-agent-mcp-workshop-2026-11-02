"""Contract tests for the MCP server, in memory, against synthetic cached responses.

Needs the workshop environment (mcp v2). Skipped automatically where the SDK is missing.
Run from the session folder:  python -m unittest tests.test_server_contract
"""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

try:
    from mcp import Client
    from mcp.types import ElicitResult

    import server
    from litreview import config, europepmc
    HAVE_SDK = True
except ImportError:  # outside the workshop environment
    HAVE_SDK = False

from tests.fakes import SEARCH_PAYLOAD


@unittest.skipUnless(HAVE_SDK, "needs the workshop environment (mcp v2)")
class ServerContract(unittest.TestCase):
    def setUp(self):
        self._saved = (config.CACHE_DIR, config.MODE)
        self._tmp = tempfile.TemporaryDirectory()
        config.CACHE_DIR, config.MODE = Path(self._tmp.name), "offline"
        url = europepmc.search_url(europepmc.build_query(config.DEFAULT_QUERY), 5)
        path = europepmc.cache_path(url)
        path.write_text(json.dumps({"url": url, "retrieved_at": "test", "payload": SEARCH_PAYLOAD}))

    def tearDown(self):
        config.CACHE_DIR, config.MODE = self._saved
        self._tmp.cleanup()

    def test_tools_resources_prompts(self):
        async def run():
            async with Client(server.mcp) as client:
                tools = {tool.name for tool in (await client.list_tools()).tools}
                result = await client.call_tool("search_literature", {"query": "", "max_results": 5})
                bad = await client.call_tool("get_paper", {"paper_id": "not-an-id"})
                guide = await client.read_resource("litreview://guide/query-syntax")
            return tools, result, bad, guide

        tools, result, bad, guide = asyncio.run(run())
        self.assertEqual(tools, {"search_literature", "get_paper", "find_citing_papers", "build_evidence_table"})
        self.assertEqual(result.structured_content["status"], "ok")
        self.assertEqual(result.structured_content["served_from"], "cache")
        self.assertTrue(getattr(bad, "is_error", False))
        self.assertIn("Europe PMC query syntax", guide.contents[0].text)

    def test_evidence_table_asks_the_user_first(self):
        asked = []

        async def answer(context, params):
            asked.append(params.message)
            return ElicitResult(action="accept", content={"from_year": 2015, "max_papers": 5,
                                                          "open_access_only": False})

        url = europepmc.search_url(europepmc.build_query(config.DEFAULT_QUERY, from_year=2015, sort="cited"), 5)
        europepmc.cache_path(url).write_text(json.dumps({"url": url, "retrieved_at": "test", "payload": SEARCH_PAYLOAD}))

        async def run():
            async with Client(server.mcp, elicitation_callback=answer) as client:
                return await client.call_tool("build_evidence_table", {})

        table = asyncio.run(run())
        self.assertTrue(asked, "the server should have asked for the scope")
        self.assertEqual(len(table.structured_content["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
