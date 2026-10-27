#!/usr/bin/env bash
# Supervisor starts MCP first, gates Jupyter on a real MCP check, and restarts failed processes.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work
exec supervisord -c scripts/supervisord.conf
