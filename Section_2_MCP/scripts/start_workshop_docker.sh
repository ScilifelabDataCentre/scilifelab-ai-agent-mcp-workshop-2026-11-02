#!/usr/bin/env bash
# Start the participant container with free loopback ports and persistent work/.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${WORKSHOP_NAME:-session2-mcp}"
IMAGE="${WORKSHOP_IMAGE:-ghcr.io/scilifelabdatacentre/ai-agents-workshop-session2:lund-2026-11-02}"
CONTAINER_DIR="/home/workshop/Section_2_MCP"
WAIT_S="${WORKSHOP_START_TIMEOUT_S:-120}"
PUBLISH_MCP=0
RECREATE=0
RESTART=0
RESTART_MCP=0
PULL=0

usage() {
  cat <<'EOF'
Usage: bash scripts/start_workshop_docker.sh [options]

  --publish-mcp   Also publish MCP on a free loopback port for laptop clients
  --restart       Restart the whole container, for example after editing .env
  --restart-mcp   Restart only the MCP process through Supervisor
  --recreate      Replace the container; keeps work/ but deletes other container files
  --pull          Pull the image before starting; use with --recreate to apply updates
  -h, --help      Show this help

Environment overrides: WORKSHOP_NAME, WORKSHOP_IMAGE, WORKSHOP_START_TIMEOUT_S.
EOF
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

while (($#)); do
  case "$1" in
    --publish-mcp) PUBLISH_MCP=1 ;;
    --recreate) RECREATE=1 ;;
    --restart) RESTART=1 ;;
    --restart-mcp) RESTART_MCP=1 ;;
    --pull) PULL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; fail "Unknown option: $1" ;;
  esac
  shift
done

if ((RECREATE && (RESTART || RESTART_MCP))); then
  fail "--recreate cannot be combined with --restart or --restart-mcp"
fi
if ((RESTART && RESTART_MCP)); then
  fail "Choose only one of --restart and --restart-mcp"
fi

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or not on PATH."
docker info >/dev/null 2>&1 || fail "Docker is not running. Start Docker Desktop and try again."
mkdir -p "$ROOT_DIR/work"

container_exists() {
  docker container inspect "$NAME" >/dev/null 2>&1
}

container_running() {
  [[ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" == "true" ]]
}

print_diagnostics() {
  echo "Container diagnostics for $NAME:" >&2
  docker logs --tail 60 "$NAME" >&2 2>/dev/null || true
  if container_running; then
    docker exec "$NAME" sh -c \
      'tail -n 60 /tmp/litreview-server.log /tmp/litreview-supervisord.log 2>/dev/null || true' >&2 || true
  fi
}

wait_for_health() {
  local deadline=$((SECONDS + WAIT_S))
  local running restarting
  echo "Waiting for MCP and Jupyter health checks (up to ${WAIT_S}s)..."
  while ((SECONDS < deadline)); do
    running="$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || true)"
    restarting="$(docker inspect -f '{{.State.Restarting}}' "$NAME" 2>/dev/null || true)"
    if [[ "$running" != "true" && "$restarting" != "true" ]]; then
      print_diagnostics
      fail "The container stopped before becoming healthy."
    fi
    # Ask the services directly. Docker's cached health status can be stale after a restart.
    if [[ "$running" == "true" ]] && \
      docker exec "$NAME" python scripts/workshop_healthcheck.py >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  print_diagnostics
  fail "The container did not become healthy within ${WAIT_S}s."
}

print_urls() {
  local jupyter_endpoint mcp_endpoint jupyter_port mcp_port
  jupyter_endpoint="$(docker port "$NAME" 7860/tcp | head -n 1 || true)"
  [[ -n "$jupyter_endpoint" ]] || fail "Docker did not publish the Jupyter port."
  jupyter_port="${jupyter_endpoint##*:}"

  echo
  echo "Workshop is ready."
  echo "JupyterLab: http://127.0.0.1:${jupyter_port}"
  echo "Notebook:   1-mcp-hands-on/mcp_literature_review_lab.ipynb"
  echo "Work files: $ROOT_DIR/work"
  echo "MCP inside the container: http://127.0.0.1:8000/mcp"

  mcp_endpoint="$(docker port "$NAME" 8000/tcp | head -n 1 || true)"
  if [[ -n "$mcp_endpoint" ]]; then
    mcp_port="${mcp_endpoint##*:}"
    echo "MCP for laptop clients:  http://127.0.0.1:${mcp_port}/mcp"
  elif ((PUBLISH_MCP)); then
    echo
    echo "This existing container has no published MCP port." >&2
    echo "Recreate it with: bash scripts/start_workshop_docker.sh --recreate --publish-mcp" >&2
  fi

  echo
  echo "Restart MCP only: bash scripts/start_workshop_docker.sh --restart-mcp"
  echo "Restart all:      bash scripts/start_workshop_docker.sh --restart"
  echo "Stop:             docker stop $NAME"
}

if ((PULL)); then
  docker pull "$IMAGE"
  if container_exists && (( ! RECREATE )); then
    echo "Image pulled. The existing container still uses its old image; use --pull --recreate to apply the update."
  fi
fi

if ((RESTART_MCP)); then
  container_exists || fail "Container $NAME does not exist. Start it without --restart-mcp first."
  container_running || fail "Container $NAME is not running. Use --restart instead."
  docker exec "$NAME" supervisorctl -c scripts/supervisord.conf restart mcp
  wait_for_health
  print_urls
  exit 0
fi

if container_exists; then
  if ((RECREATE)); then
    echo "Replacing container $NAME. The host work/ folder is kept."
    docker rm -f "$NAME" >/dev/null
  elif ((RESTART)); then
    docker restart "$NAME" >/dev/null
    wait_for_health
    print_urls
    exit 0
  else
    if ! container_running; then
      docker start "$NAME" >/dev/null
    fi
    wait_for_health
    print_urls
    exit 0
  fi
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker pull "$IMAGE"
fi

run_args=(
  -d
  --name "$NAME"
  --restart "on-failure:3"
  -e "WORKSHOP_LOCAL_NO_AUTH=1"
  -p "127.0.0.1::7860"
  -v "$ROOT_DIR/work:$CONTAINER_DIR/work"
)

if ((PUBLISH_MCP)); then
  run_args+=(-p "127.0.0.1::8000")
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  run_args+=(-v "$ROOT_DIR/.env:$CONTAINER_DIR/.env:ro")
else
  echo "No .env found. Non-model steps work; create .env before using OpenLLM."
fi

# A real shell environment overrides values loaded from the mounted .env file.
for variable in \
  LLM_PROVIDER OPENLLM_API_KEY OPENLLM_BASE_URL OPENLLM_MODEL OPENLLM_DISABLE_THINKING \
  OPENAI_API_KEY OPENAI_MODEL LITREVIEW_MODE LITREVIEW_DEFAULT_QUESTION LITREVIEW_DEFAULT_QUERY; do
  if printenv "$variable" >/dev/null 2>&1; then
    run_args+=(-e "$variable")
  fi
done

run_args+=("$IMAGE")
docker run "${run_args[@]}" >/dev/null
wait_for_health
print_urls
