#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
ADMIN_DIR="$ROOT_DIR/admin"
PIDS=()

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  ./start.sh            Install dependencies and start backend + frontend + admin locally
  ./start.sh --docker   Create .env if needed, then run docker compose up -d --build
  ./start.sh --help     Show this help

Local URLs:
  Frontend: http://localhost:8080
  Admin:    http://localhost:8082
  API docs: http://localhost:8081/api/v1/docs
EOF
}

ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ ! -f "$ENV_EXAMPLE" ]]; then
      echo "Missing .env and .env.example." >&2
      exit 1
    fi
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    log "Created .env from .env.example. Update GEMINI_API_KEY in .env when you need real AI responses."
  fi

  while IFS='=' read -r key value || [[ -n "${key:-}" ]]; do
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ -z "$key" || "$key" == \#* ]] && continue
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    export "$key=$value"
  done < "$ENV_FILE"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

pick_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Missing Python. Install Python 3.11 for the backend." >&2
    exit 1
  fi

  PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$PYTHON_VERSION" != "3.11" ]]; then
    log "Warning: backend is tested with Python 3.11, but $PYTHON_BIN is Python $PYTHON_VERSION."
  fi
}

install_backend() {
  pick_python
  log "Installing backend dependencies"
  cd "$BACKEND_DIR"
  if [[ ! -d ".venv" ]]; then
    "$PYTHON_BIN" -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
}

install_node_app() {
  local app_dir="$1"
  local app_name="$2"

  require_command npm
  log "Installing $app_name dependencies"
  cd "$app_dir"
  npm ci
}

start_process() {
  local name="$1"
  shift
  log "Starting $name"
  "$@" &
  PIDS+=("$!")
}

cleanup() {
  if [[ "${#PIDS[@]}" -gt 0 ]]; then
    log "Stopping services"
    kill "${PIDS[@]}" >/dev/null 2>&1 || true
    wait "${PIDS[@]}" >/dev/null 2>&1 || true
  fi
}

start_local() {
  ensure_env_file
  install_backend
  install_node_app "$FRONTEND_DIR" "frontend"
  install_node_app "$ADMIN_DIR" "admin"

  trap cleanup EXIT INT TERM

  BACKEND_PORT="${BACKEND_PORT:-8081}"
  FRONTEND_PORT="${FRONTEND_PORT:-8080}"
  ADMIN_PORT="${ADMIN_PORT:-8082}"

  start_process "backend on http://localhost:$BACKEND_PORT" \
    bash -c "cd '$BACKEND_DIR' && source .venv/bin/activate && exec uvicorn app.main:app --host 127.0.0.1 --port '$BACKEND_PORT'"

  start_process "frontend on http://localhost:$FRONTEND_PORT" \
    bash -c "cd '$FRONTEND_DIR' && exec npm run dev"

  start_process "admin on http://localhost:$ADMIN_PORT" \
    bash -c "cd '$ADMIN_DIR' && exec npm run dev"

  log "All services are starting"
  printf 'Frontend: http://localhost:%s\n' "$FRONTEND_PORT"
  printf 'Admin:    http://localhost:%s\n' "$ADMIN_PORT"
  printf 'API docs: http://localhost:%s/api/v1/docs\n' "$BACKEND_PORT"
  printf '\nPress Ctrl+C to stop all local services.\n'

  wait
}

start_docker() {
  ensure_env_file
  require_command docker
  log "Building and starting Docker services"
  cd "$ROOT_DIR"
  docker compose up -d --build
  log "Docker services started"
  printf 'Frontend: http://localhost:%s\n' "${FRONTEND_PORT:-8080}"
  printf 'Admin:    http://localhost:%s\n' "${ADMIN_PORT:-8082}"
  printf 'API docs: http://localhost:%s/api/v1/docs\n' "${BACKEND_PORT:-8081}"
}

case "${1:-}" in
  --docker)
    start_docker
    ;;
  --help|-h)
    usage
    ;;
  "")
    start_local
    ;;
  *)
    usage
    exit 1
    ;;
esac
