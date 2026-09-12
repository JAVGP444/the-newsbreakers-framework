#!/usr/bin/env bash
# Observatorio en Linux (Debian/Ubuntu/Fedora). Equivalente a mac/Instalar-y-abrir.command
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

API_PORT=8010
WEB_PORT=5173
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

if ! command -v python3 >/dev/null; then
  echo "Falta python3. En Debian: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi
if ! command -v npm >/dev/null; then
  echo "Falta Node.js / npm."
  exit 1
fi

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  python3 -m venv "$ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
python -m pip install -q -r "$ROOT/requirements.txt"
( cd "$ROOT/frontend" && npm install )

if [ ! -f "$ROOT/.env" ] && [ -f "$ROOT/.env.example" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Creado .env desde .env.example"
fi

port_listening() { ss -ltn 2>/dev/null | grep -q ":$1 " || netstat -ltn 2>/dev/null | grep -q ":$1 "; }

if ! port_listening "$API_PORT"; then
  nohup python -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT" \
    >>"$LOG_DIR/linux-api.log" 2>&1 &
fi
if ! port_listening "$WEB_PORT"; then
  nohup npm --prefix "$ROOT/frontend" run dev -- --host 127.0.0.1 --port "$WEB_PORT" \
    >>"$LOG_DIR/linux-web.log" 2>&1 &
fi
sleep 3
echo "Observatorio (ventana): http://127.0.0.1:${WEB_PORT}/#/"
echo "API:          http://127.0.0.1:${API_PORT}"
nohup python "$ROOT/desktop/open.py" --url "http://127.0.0.1:${WEB_PORT}/#/" >>"$LOG_DIR/desktop.log" 2>&1 &
