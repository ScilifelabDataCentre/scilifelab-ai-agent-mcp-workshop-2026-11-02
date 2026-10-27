"""Local tests for the Docker health checks. No workshop packages or network are needed."""

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mcp_health import PROTOCOL, check_mcp  # noqa: E402
from workshop_healthcheck import check_jupyter  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def send_payload(self, payload, content_type="application/json"):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.path != "/mcp":
            self.send_error(404)
            return
        if self.server.mode == "empty":
            self.send_payload({"jsonrpc": "2.0", "id": 1})
        elif self.server.mode == "wrong-version":
            self.send_payload({
                "jsonrpc": "2.0", "id": 1,
                "result": {"supportedVersions": ["1999-01-01"]},
            })
        elif self.server.mode == "sse":
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"supportedVersions": [PROTOCOL]}})
            self.send_payload(f"data: {payload}\n\n".encode("utf-8"), "text/event-stream")
        else:
            self.send_payload({
                "jsonrpc": "2.0", "id": 1,
                "result": {"supportedVersions": [PROTOCOL]},
            })

    def do_GET(self):
        if self.path == "/api":
            self.send_payload({"version": "test"})
        elif self.path == "/api-authenticated":
            self.send_error(403)
        elif self.path == "/api-login-redirect":
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


class WorkshopHealthTests(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.mode = "good"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    def test_real_mcp_discover_check_passes(self):
        healthy, detail = check_mcp(f"{self.base}/mcp", timeout=1)
        self.assertTrue(healthy, detail)

    def test_jupyter_api_check_passes(self):
        healthy, detail = check_jupyter(f"{self.base}/api", timeout=1)
        self.assertTrue(healthy, detail)

    def test_jupyter_authentication_response_is_healthy(self):
        healthy, detail = check_jupyter(f"{self.base}/api-authenticated", timeout=1)
        self.assertTrue(healthy, detail)
        self.assertIn("requires authentication", detail)

    def test_jupyter_login_redirect_is_healthy(self):
        healthy, detail = check_jupyter(f"{self.base}/api-login-redirect", timeout=1)
        self.assertTrue(healthy, detail)
        self.assertIn("login", detail)

    def test_plain_http_200_is_not_mcp_health(self):
        self.httpd.mode = "empty"
        healthy, detail = check_mcp(f"{self.base}/mcp", timeout=1)
        self.assertFalse(healthy)
        self.assertIn("no result", detail)

    def test_wrong_protocol_is_rejected(self):
        self.httpd.mode = "wrong-version"
        healthy, detail = check_mcp(f"{self.base}/mcp", timeout=1)
        self.assertFalse(healthy)
        self.assertIn("not supported", detail)

    def test_event_stream_response_is_accepted(self):
        self.httpd.mode = "sse"
        healthy, detail = check_mcp(f"{self.base}/mcp", timeout=1)
        self.assertTrue(healthy, detail)


if __name__ == "__main__":
    unittest.main()
