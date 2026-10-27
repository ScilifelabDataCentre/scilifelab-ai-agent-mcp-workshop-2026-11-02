#!/usr/bin/env bash
# Do not expose an unfinished workshop: start Jupyter only after MCP answers server/discover.
set -euo pipefail
cd "$(dirname "$0")/.."

MCP_HEALTH_URL="http://127.0.0.1:${MCP_PORT:-8000}/mcp"
TIMEOUT_S="${MCP_START_TIMEOUT_S:-60}"

for ((elapsed = 0; elapsed < TIMEOUT_S; elapsed++)); do
  if python scripts/mcp_health.py --url "$MCP_HEALTH_URL" --quiet; then
    echo "MCP is healthy at $MCP_HEALTH_URL"
    echo "Starting JupyterLab on container port ${JUPYTER_PORT:-7860}"

    jupyter_args=(
      lab --ip=0.0.0.0 --port="${JUPYTER_PORT:-7860}" --no-browser
      --ServerApp.root_dir="$PWD"
    )
    if [[ "${WORKSHOP_LOCAL_NO_AUTH:-0}" == "1" ]]; then
      # The participant launcher publishes only to 127.0.0.1. Never use this on Serve.
      echo "Local loopback mode: JupyterLab authentication is disabled"
      jupyter_args+=(--ServerApp.token='' --ServerApp.password='')
    elif [[ -n "${JUPYTER_TOKEN:-}" ]]; then
      echo "JupyterLab authentication is enabled with JUPYTER_TOKEN"
      jupyter_args+=(--ServerApp.token="$JUPYTER_TOKEN")
    else
      # Jupyter generates a random token and prints it in the application logs.
      echo "JupyterLab authentication is enabled; find the generated token in the logs"
    fi
    exec jupyter "${jupyter_args[@]}"
  fi
  sleep 1
done

echo "MCP did not become healthy within ${TIMEOUT_S}s. See /tmp/litreview-server.log." >&2
tail -n 50 /tmp/litreview-server.log >&2 2>/dev/null || true
exit 1
