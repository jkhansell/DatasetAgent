#!/bin/bash
set -euo pipefail

export ROOT=$(git rev-parse --show-toplevel)

source $ROOT/.env
source $ROOT/.venv/bin/activate


ROOT=$(pwd)
LOG_DIR="$ROOT/logs"
PID_DIR="$ROOT/pids"

VLLM_PORT=9000
LANGRAPH_PORT=9001
FRONTEND_PORT=9002

mkdir -p "$LOG_DIR" "$PID_DIR"

# =========================
# Helper functions
# =========================

is_port_in_use() {
  local port=$1
  lsof -i :$port > /dev/null 2>&1
}

free_port_if_needed() {
  local port=$1
  local name=$2

  if is_port_in_use "$port"; then
    echo "[WARN] Port $port in use for $name"

    # Check if it's OUR process
    local pid_file="$PID_DIR/$name.pid"
    if [ -f "$pid_file" ]; then
      local pid
      pid=$(cat "$pid_file")

      if lsof -i :$port | grep -q "$pid"; then
        echo "[INFO] Port belongs to tracked process ($name), leaving it"
        return
      fi
    fi

    echo "[ACTION] Freeing port $port"
    kill -9 $(lsof -t -i:$port) 2>/dev/null || true
    sleep 2
  fi
}

is_running() {
  local pid_file=$1
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
      return 0
    else
      echo "Stale PID found in $pid_file, removing"
      rm -f "$pid_file"
      echo "Sleeping for 10 seconds to allow system to update process list"
      sleep 10
      return 1
    fi
  fi
  return 1
}

start_process() {
  local name=$1
  local cmd=$2
  local port=$3
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  free_port_if_needed "$port" "$name"

  if is_running "$pid_file"; then
    echo "[SKIP] $name already running (PID $(cat $pid_file))"
  else
    echo "[START] $name"
    bash -c "stdbuf -oL -eL bash -c '$cmd'" > "$log_file" 2>&1 &
    echo $! > "$pid_file"
  fi
}


stop_all() {
  echo "Stopping all services..."
  pkill -u jovillalobos
  echo "All services stopped."
}


# =========================
# ACTION
# =========================
ACTION=${1:-start}

case "$ACTION" in
  start)
    echo "Starting services..."

    # =========================
# Start services
# =========================

  start_process "vllm" "
vllm serve Qwen/Qwen3.5-9B \
  --port $VLLM_PORT \
  --max-model-len 100K \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.925 \
  --served-model-name gemma4-agent \
  --dtype auto
" $VLLM_PORT

#  start_process "langgraph" "
#cd $ROOT/agent && uv run langgraph dev --port $LANGRAPH_PORT
#" $LANGRAPH_PORT

#  start_process "frontend" "
#cd $ROOT/agent-chat-ui && PORT=$FRONTEND_PORT pnpm dev
#" $FRONTEND_PORT

  echo "All services checked."
    ;;

  stop)
    stop_all
    ;;

  restart)
    stop_all
    sleep 2
    echo "Restarting..."
    exec "$0" start
    ;;

  *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac