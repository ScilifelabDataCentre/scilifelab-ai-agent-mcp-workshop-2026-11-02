"""HTTP-route contract tests for the combined MCP server."""

from __future__ import annotations

import unittest

try:
    import server
    HAVE_SDK = True
except ImportError:
    HAVE_SDK = False


class ServeSetupTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_SDK, "needs mcp v2")
    def test_root_and_health_routes_are_registered(self):
        routes = {route.path for route in server.mcp._custom_starlette_routes}
        self.assertEqual(routes, {"/", "/health"})
        self.assertTrue(all("GET" in route.methods for route in server.mcp._custom_starlette_routes))


if __name__ == "__main__":
    unittest.main()
