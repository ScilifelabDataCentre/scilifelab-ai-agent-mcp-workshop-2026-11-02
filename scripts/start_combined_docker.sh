#!/usr/bin/env bash
# Local combined-workshop launcher. Host publications are always loopback-only.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
NAME=${WORKSHOP_CONTAINER_NAME:-ai-agents-workshop}
IMAGE=${WORKSHOP_IMAGE:-ai-agents-workshop:local}
BUILD=0
RECREATE=0
PULL=0
PUBLISH_MCP=0
ACTION=start
PLATFORM=${WORKSHOP_PLATFORM:-}

usage() {
  cat <<'EOF'
Usage: bash scripts/start_combined_docker.sh [options]

  --build         Build WORKSHOP_IMAGE from the repository root first
  --pull          Pull WORKSHOP_IMAGE before starting
  --recreate      Replace the existing container (keeps the host work/ directory)
  --publish-mcp   Also publish MCP on an automatic 127.0.0.1 host port
  --restart       Restart the whole container
  --restart-mcp   Restart only MCP through Supervisor
  --status        Show container and process status
  -h, --help      Show this help

Environment overrides: WORKSHOP_IMAGE, WORKSHOP_CONTAINER_NAME, and WORKSHOP_PLATFORM.
WORKSHOP_PLATFORM may be linux/amd64 or linux/arm64; the default auto-detects Docker's host.
If .env exists, Docker reads it with --env-file; it is never copied into the image.
EOF
}

while (($#)); do
  case "$1" in
    --build) BUILD=1 ;;
    --pull) PULL=1 ;;
    --recreate) RECREATE=1 ;;
    --publish-mcp) PUBLISH_MCP=1 ;;
    --restart) ACTION=restart ;;
    --restart-mcp) ACTION=restart-mcp ;;
    --status) ACTION=status ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed or not on PATH" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "The Docker daemon is not available" >&2; exit 1; }

case "$ACTION" in
  restart)
    docker restart "$NAME" >/dev/null
    echo "Restarted $NAME"
    exit 0
    ;;
  restart-mcp)
    docker exec "$NAME" supervisorctl -c scripts/supervisord.conf restart mcp
    exit 0
    ;;
  status)
    docker ps -a --filter "name=^/${NAME}$"
    docker exec "$NAME" supervisorctl -c scripts/supervisord.conf status
    exit 0
    ;;
esac

if [[ -z "$PLATFORM" ]]; then
  DOCKER_ARCH=$(docker info --format '{{.Architecture}}')
  case "$DOCKER_ARCH" in
    x86_64|amd64) PLATFORM=linux/amd64 ;;
    aarch64|arm64) PLATFORM=linux/arm64 ;;
    *) echo "Unsupported Docker architecture: $DOCKER_ARCH; set WORKSHOP_PLATFORM explicitly" >&2; exit 1 ;;
  esac
fi
case "$PLATFORM" in
  linux/amd64|linux/arm64) ;;
  *) echo "WORKSHOP_PLATFORM must be linux/amd64 or linux/arm64" >&2; exit 2 ;;
esac
echo "Using container platform $PLATFORM"

if ((BUILD)); then
  docker build --platform "$PLATFORM" -t "$IMAGE" "$ROOT_DIR"
fi
if ((PULL)); then
  docker pull --platform "$PLATFORM" "$IMAGE"
fi

if docker container inspect "$NAME" >/dev/null 2>&1; then
  if ((RECREATE)); then
    docker rm -f "$NAME" >/dev/null
  else
    if [[ $(docker inspect -f '{{.State.Running}}' "$NAME") != true ]]; then
      docker start "$NAME" >/dev/null
    fi
    echo "Using existing container $NAME. Use --recreate after image or configuration changes."
  fi
fi

if ! docker container inspect "$NAME" >/dev/null 2>&1; then
  mkdir -p "$ROOT_DIR/work"
  run_args=(
    -d
    --name "$NAME"
    --platform "$PLATFORM"
    --restart on-failure:3
    -e WORKSHOP_LOCAL_NO_AUTH=1
    -p 127.0.0.1::7860
    -v "$ROOT_DIR/work:/home/workshop/app/work"
  )
  if [[ -f "$ROOT_DIR/.env" ]]; then
    run_args+=(--env-file "$ROOT_DIR/.env")
  fi
  if ((PUBLISH_MCP)); then
    run_args+=(-p 127.0.0.1::8000)
  fi
  docker run "${run_args[@]}" "$IMAGE" >/dev/null
fi

healthy=0
for _attempt in $(seq 1 120); do
  if docker exec "$NAME" python scripts/workshop_healthcheck.py >/dev/null 2>&1; then
    healthy=1
    break
  fi
  if [[ $(docker inspect -f '{{.State.Running}}' "$NAME") != true ]]; then
    break
  fi
  sleep 1
done

if ((!healthy)); then
  echo "The combined workshop did not become healthy. Recent logs:" >&2
  docker logs --tail 100 "$NAME" >&2 || true
  exit 1
fi

JUPYTER_ADDRESS=$(docker port "$NAME" 7860/tcp | head -n 1)
echo "JupyterLab: http://${JUPYTER_ADDRESS}"
echo "Open Section_1_LangGraph/langgraph_lab.ipynb or Section_2_MCP/1-mcp-hands-on/mcp_literature_review_lab.ipynb"
if ((PUBLISH_MCP)); then
  MCP_ADDRESS=$(docker port "$NAME" 8000/tcp | head -n 1)
  echo "External MCP URL: http://${MCP_ADDRESS}/mcp"
fi
echo "Persistent files: $ROOT_DIR/work"
