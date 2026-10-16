#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🎲 Launching Aatam: The Board Game Wiki on Steroids..."
"$DIR/.venv/bin/uvicorn" backend.server:app --host 0.0.0.0 --port 8000
