#!/usr/bin/env bash
# Rehearsal smoke test: unit tests, server contract tests, then the real server over HTTP.
#   bash scripts/smoke_test.sh            (from the Section_2_MCP folder, in the workshop environment)
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${SMOKE_PORT:-8765}"

echo "== unit and contract tests"
python -m unittest discover -s . -p "test_*.py" -t .

echo "== start the server on port $PORT"
python server.py --port "$PORT" > /tmp/smoke-server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/mcp"; then break; fi
  sleep 1
done

echo "== real MCP health check"
python scripts/mcp_health.py --url "http://127.0.0.1:$PORT/mcp"

echo "== raw HTTP (2026-07-28)"
MCP_URL="http://127.0.0.1:$PORT/mcp" bash 3-bonus-one-server-many-hosts/hosts/raw_http.sh

echo "== SDK client, no language model"
MCP_URL="http://127.0.0.1:$PORT/mcp" python client_demo.py

echo "== ask the user, on the wire"
MCP_URL="http://127.0.0.1:$PORT/mcp" python 2-bonus-ask-the-user/ask_the_user.py --wire

echo "Smoke test passed. Next: run the solution notebook top to bottom with a workshop key."
