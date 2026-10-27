"""Docker health check for both the internal MCP server and combined JupyterLab."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from mcp_health import DEFAULT_URL, check_mcp

DEFAULT_JUPYTER_URL = f"http://127.0.0.1:{os.environ.get('JUPYTER_PORT', '7860')}/api"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def check_jupyter(url: str = DEFAULT_JUPYTER_URL, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with _OPENER.open(url, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return True, f"Jupyter API is alive and requires authentication (HTTP {exc.code})"
        location = exc.headers.get("Location", "")
        if exc.code in {301, 302, 303, 307, 308} and "/login" in location:
            return True, "Jupyter is alive and redirects to its login page"
        return False, f"Jupyter returned HTTP {exc.code}"
    except Exception as exc:
        return False, f"Jupyter check failed: {type(exc).__name__}: {exc}"
    if status != 200 or not isinstance(payload, dict):
        return False, f"Jupyter returned HTTP {status}"
    return True, "Jupyter API succeeded"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-url", default=os.environ.get("MCP_HEALTH_URL", DEFAULT_URL))
    parser.add_argument("--jupyter-url", default=os.environ.get("JUPYTER_HEALTH_URL", DEFAULT_JUPYTER_URL))
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    healthy, detail = check_mcp(args.mcp_url, args.timeout)
    if not healthy:
        print(detail)
        return 1
    healthy, detail = check_jupyter(args.jupyter_url, args.timeout)
    if not healthy:
        print(detail)
        return 1
    print("Combined workshop is healthy: MCP discovery and JupyterLab both succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
