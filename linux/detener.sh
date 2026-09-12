#!/usr/bin/env bash
set -euo pipefail
for port in 8010 5173; do
  pids="$(ss -lptn "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | sort -u)"
  if [ -z "$pids" ]; then
    pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  if [ -n "${pids:-}" ]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    echo "Puerto $port cerrado"
  else
    echo "Puerto $port: nada"
  fi
done
pkill -f "mine_loop.py" 2>/dev/null || true
pkill -f "desktop/open.py" 2>/dev/null || true
echo "Listo."
