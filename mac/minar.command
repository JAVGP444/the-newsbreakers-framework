#!/bin/bash
# Minería continua en macOS — primer plano, logs visibles.
# El sleep/hibernación del Mac pausa el bucle (deja el portátil despierto).
#
#   chmod +x mac/minar.command
#   ./mac/minar.command
#
# Para ver el contador subir YA (varios ciclos seguidos): mac/minar-ya.command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
MINE_LOG="$LOG_DIR/mac-mine.log"
PID_FILE="$LOG_DIR/mac-mine.pid"
PY="$ROOT/.venv/bin/python"

mkdir -p "$LOG_DIR"

if [ ! -x "$PY" ]; then
  echo "No hay .venv de macOS ($PY)."
  echo "Ejecuta primero Instalar-y-abrir.command"
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

export TNB_DEMO_SEED=0
export TNB_FAST=0
export TNB_FORCE_DUE="${TNB_FORCE_DUE:-0}"
export TNB_MAX_SOURCES="${TNB_MAX_SOURCES:-250}"
export TNB_RSS_LIMIT="${TNB_RSS_LIMIT:-100}"
export TNB_GDELT_MAX="${TNB_GDELT_MAX:-75}"
export TNB_HTML_LISTINGS="${TNB_HTML_LISTINGS:-1}"
export TNB_HTML_LISTING_SOURCES="${TNB_HTML_LISTING_SOURCES:-10}"
export TNB_HTML_FETCH_PER_SOURCE="${TNB_HTML_FETCH_PER_SOURCE:-8}"
export PYTHONUNBUFFERED=1

echo "=== The NewsBreakers — minero (Mac, primer plano) ==="
echo "Repo:     $ROOT"
echo "Python:   $PY ($("$PY" --version 2>&1))"
echo "TNB_FAST=$TNB_FAST  TNB_DEMO_SEED=$TNB_DEMO_SEED  TNB_MAX_SOURCES=$TNB_MAX_SOURCES"
echo "TNB_DEMO_ROOT opcional (sin Generador se usa config/watchlist.yaml)."
echo "Log también en: $MINE_LOG"
echo "Ctrl+C para parar. El sleep del Mac pausa la minería."
echo ""

echo $$ > "$PID_FILE"
cleanup() { rm -f "$PID_FILE"; }
trap cleanup EXIT

echo "----- $(date '+%Y-%m-%d %H:%M:%S') mine_loop -----" | tee -a "$MINE_LOG"
"$PY" -u "$ROOT/mine_loop.py" 2>&1 | tee -a "$MINE_LOG"
