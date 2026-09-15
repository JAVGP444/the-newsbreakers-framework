#!/bin/bash
# Prepara venv y archivos. No abre ventana: eso lo hace el binario nativo.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
LOG="$HOME/Library/Logs/NewsBreakers.log"
SUPPORT="$HOME/Library/Application Support/TheNewsBreakers"
HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$(cd "$HERE/.." && pwd)"
SRC="$HERE/framework"
mkdir -p "$SUPPORT" "$(dirname "$LOG")"

say_err() {
  osascript -e "display dialog \"$1\" buttons {\"OK\"} default button 1 with title \"The NewsBreakers\"" >/dev/null 2>&1 || true
}

{
  echo "===== setup $(date) ====="
  echo "bundle=$BUNDLE"

  PY=""
  for c in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$(command -v "$c" 2>/dev/null || echo "$c")"
      break
    fi
  done
  if [ -z "$PY" ]; then
    say_err "Falta Python 3.9 o superior. Instálalo con brew install python y vuelve a abrir la app."
    exit 1
  fi

  # Una API vieja en otro puerto deja la sala “sin servidor” y bloquea SQLite.
  pkill -f "desktop/app.py --serve" >/dev/null 2>&1 || true
  sleep 0.2

  rsync -a \
    --exclude '.git/' --exclude '.venv/' --exclude 'node_modules/' \
    --exclude 'frontend/node_modules/' --exclude 'logs/' \
    --exclude 'data/license.key' --exclude '.env' \
    --exclude 'data/processed/' --exclude 'storage/' \
    --exclude '__pycache__/' --exclude '.pytest_cache/' \
    "$SRC/" "$SUPPORT/"
  cd "$SUPPORT"

  if [ ! -x .venv/bin/python ]; then
    "$PY" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  DEPS=requirements-desktop.txt
  if [ ! -f "$DEPS" ]; then DEPS=requirements.txt; fi
  HASH_FILE=".venv/.tnb-reqs.sha"
  REQ_HASH="$(shasum -a 256 "$DEPS" | awk '{print $1}')"
  NEED_PIP=0
  if [ ! -f "$HASH_FILE" ] || [ "$(cat "$HASH_FILE" 2>/dev/null)" != "$REQ_HASH" ]; then
    NEED_PIP=1
  fi
  if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    NEED_PIP=1
  fi
  if [ "$NEED_PIP" = 1 ]; then
    python -m pip install -q -U pip
    python -m pip install -q -r "$DEPS"
    echo "$REQ_HASH" >"$HASH_FILE"
  fi

  if [ ! -f frontend/dist/index.html ]; then
    if ! command -v npm >/dev/null; then
      say_err "Falta la interfaz compilada y no hay Node.js. Instala Node desde https://nodejs.org y vuelve a abrir."
      exit 1
    fi
    (cd frontend && npm install && VITE_API_URL= npm run build)
  fi
  if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
  fi
  echo "$SUPPORT/.venv/bin/python"
} >>"$LOG" 2>&1
