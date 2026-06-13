#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
report="$project_dir/outputs/latest-digest.md"

if [[ ! -f "$report" ]]; then
  echo "No report exists yet. Run:"
  echo "  $project_dir/scripts/monitor.sh"
  exit 1
fi

cat "$report"
