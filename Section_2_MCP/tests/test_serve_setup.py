"""Serve packaging and HTTP-route contract tests."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import server
    HAVE_SDK = True
except ImportError:
    HAVE_SDK = False


class ServeSetupTests(unittest.TestCase):
    def test_strict_preflight(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/preflight.py"), "--root", str(ROOT), "--strict"],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAVE_SDK, "needs mcp v2")
    def test_root_and_health_routes_are_registered(self):
        routes = {route.path for route in server.mcp._custom_starlette_routes}
        self.assertEqual(routes, {"/", "/health"})
        self.assertTrue(all("GET" in route.methods for route in server.mcp._custom_starlette_routes))


if __name__ == "__main__":
    unittest.main()
