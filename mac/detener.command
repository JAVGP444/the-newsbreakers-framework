#!/bin/bash
# The NewsBreakers — detiene API (8010) y dashboard (5173) en macOS.
#
# Doble clic en Finder, o:
#   chmod +x detener.command
#   ./detener.command

set -euo pipefail

echo "=== The NewsBreakers — detener (Mac) ==="

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    echo "Puerto $port: nada escuchando"
    return 0
  fi
  echo "Puerto $port: deteniendo PID $pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 1
  pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
    echo "Puerto $port: forzado (PID $pids)"
  else
    echo "Puerto $port: cerrado"
  fi
}

kill_port 8010
kill_port 5173

echo "Listo."
echo ""
