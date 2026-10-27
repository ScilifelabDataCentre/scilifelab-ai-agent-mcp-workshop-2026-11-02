#!/usr/bin/env bash
# Serve entrypoint: Supervisor starts MCP, gates Jupyter on MCP health, and restarts failures.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work Section_2_MCP/work
exec supervisord -c scripts/supervisord.conf
