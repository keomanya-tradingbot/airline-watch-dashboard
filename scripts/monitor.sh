#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ -x .venv/bin/airline-watch ]]; then
  airline_watch=(.venv/bin/airline-watch)
elif command -v airline-watch >/dev/null 2>&1; then
  airline_watch=(airline-watch)
else
  echo "Airline Watch is not installed. Run:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -e '.[dev]'"
  exit 1
fi

mkdir -p outputs
"${airline_watch[@]}" run
"${airline_watch[@]}" digest \
  --hours "${AIRLINE_WATCH_REPORT_HOURS:-168}" \
  --output outputs/latest-digest.md
"${airline_watch[@]}" dashboard \
  --hours "${AIRLINE_WATCH_DASHBOARD_HOURS:-720}" \
  --output outputs/dashboard.html
cp outputs/dashboard.html outputs/index.html

echo
echo "Latest report: $project_dir/outputs/latest-digest.md"
echo "Dashboard: $project_dir/outputs/dashboard.html"
