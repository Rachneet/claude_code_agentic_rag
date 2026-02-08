#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Kill existing processes on our ports and wait for release
kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Killing processes on port $port (PIDs: $pids)"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    # Wait until port is free
    for i in $(seq 1 10); do
      if ! lsof -ti :"$port" >/dev/null 2>&1; then
        break
      fi
      sleep 0.3
    done
  fi
}

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}

trap cleanup SIGINT SIGTERM

# Kill anything already running on our ports
kill_port 8000
kill_port 5173

# Start backend
echo "Starting backend..."
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both services"
echo ""

wait
