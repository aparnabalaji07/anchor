#!/usr/bin/env bash
# Starts the backend (port 8000) and frontend (port 5173) together.
# Press Ctrl+C once to stop both.
set -e
cd "$(dirname "$0")"

for port in 8000 5173; do
  if lsof -nP -iTCP:$port -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Close the other terminal running it, then try again."
    exit 1
  fi
done

if [ ! -x backend/.venv/bin/uvicorn ]; then
  echo "Backend is not set up. Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend packages..."
  (cd frontend && npm install)
fi

# Stop both servers when this script exits
trap 'kill 0' EXIT

(cd backend && .venv/bin/uvicorn app.main:app --reload) &
(cd frontend && npm run dev) &

echo ""
echo "Backend:  http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."
wait
