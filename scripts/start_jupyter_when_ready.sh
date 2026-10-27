#!/usr/bin/env bash
# Start one authenticated-by-default JupyterLab after MCP answers server/discover.
set -euo pipefail
cd "$(dirname "$0")/.."

MCP_HEALTH_URL="http://127.0.0.1:${MCP_PORT:-8000}/mcp"
TIMEOUT_S="${MCP_START_TIMEOUT_S:-90}"

for ((elapsed = 0; elapsed < TIMEOUT_S; elapsed++)); do
  if python scripts/mcp_health.py --url "$MCP_HEALTH_URL" --quiet; then
    echo "MCP is healthy at $MCP_HEALTH_URL"
    echo "Starting combined JupyterLab on container port ${JUPYTER_PORT:-7860}"
    echo "Workshop directories: Section_1_LangGraph and Section_2_MCP"

    jupyter_args=(
      lab --ip=0.0.0.0 --port="${JUPYTER_PORT:-7860}" --no-browser
      --ServerApp.root_dir="$PWD"
    )
    if [[ "${WORKSHOP_LOCAL_NO_AUTH:-0}" == "1" ]]; then
      # Only the local launcher enables this, with Jupyter published on 127.0.0.1.
      echo "Local loopback mode: JupyterLab authentication is disabled"
      jupyter_args+=(--ServerApp.token='' --ServerApp.password='')
    elif [[ -n "${JUPYTER_TOKEN:-}" ]]; then
      echo "JupyterLab authentication is enabled with JUPYTER_TOKEN"
      jupyter_args+=(--ServerApp.token="$JUPYTER_TOKEN")
    else
      echo "JupyterLab authentication is enabled; find the generated token in the logs"
    fi
    exec jupyter "${jupyter_args[@]}"
  fi
  sleep 1
done

echo "MCP did not become healthy within ${TIMEOUT_S}s. See /tmp/combined-workshop-mcp.log." >&2
tail -n 50 /tmp/combined-workshop-mcp.log >&2 2>/dev/null || true
exit 1
