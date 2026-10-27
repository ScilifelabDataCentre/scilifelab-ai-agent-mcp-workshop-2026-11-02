"""Check that an MCP endpoint answers a real server/discover request."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request

PROTOCOL = "2026-07-28"
DEFAULT_URL = f"http://127.0.0.1:{os.environ.get('MCP_PORT', '8000')}/mcp"


def _decode_response(raw: bytes, content_type: str) -> dict:
    text = raw.decode("utf-8")
    if "text/event-stream" in content_type:
        chunks = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        for chunk in reversed(chunks):
            try:
                return json.loads(chunk)
            except ValueError:
                continue
        raise ValueError("No JSON data found in the event stream")
    return json.loads(text)


def check_mcp(url: str = DEFAULT_URL, timeout: float = 3.0) -> tuple[bool, str]:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "server/discover",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": PROTOCOL,
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": {"name": "workshop-healthcheck", "version": "1.0"},
            }
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
            "Mcp-Method": "server/discover",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = getattr(response, "status", response.getcode())
            content_type = response.headers.get("content-type", "")
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if status != 200:
        return False, f"HTTP {status}"
    try:
        payload = _decode_response(raw, content_type)
    except (UnicodeDecodeError, ValueError) as exc:
        return False, f"Invalid MCP response: {exc}"
    if payload.get("error"):
        return False, f"MCP error: {payload['error']}"
    result = payload.get("result")
    if not isinstance(result, dict):
        return False, "MCP response has no result object"
    versions = result.get("supportedVersions")
    if isinstance(versions, list) and versions and PROTOCOL not in versions:
        return False, f"Protocol {PROTOCOL} is not supported"
    return True, "MCP server/discover succeeded"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("MCP_HEALTH_URL", DEFAULT_URL))
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    healthy, detail = check_mcp(args.url, args.timeout)
    if not args.quiet:
        print(detail)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
