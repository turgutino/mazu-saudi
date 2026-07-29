#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_PORT="${MAZU_APP_PORT:-8765}"

cd "$PROJECT_ROOT"

if [ ! -d competition_app/node_modules ]; then
  npm --prefix competition_app ci
fi

npm --prefix competition_app run build

PYTHONPATH=src conda run -n ml python scripts/run_competition_app.py \
  --host 127.0.0.1 \
  --port "$APP_PORT"
