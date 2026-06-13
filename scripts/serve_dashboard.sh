#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
port="${AIRLINE_WATCH_PORT:-8765}"

echo "Serving Airline Watch at http://localhost:$port"
echo "Keep this terminal open while using the dashboard."
echo "Press Ctrl+C to stop."
cd "$project_dir"
exec .venv/bin/python -m http.server "$port" --directory outputs
