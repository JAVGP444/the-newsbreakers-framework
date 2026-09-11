#!/bin/bash
# Minería continua en macOS (RSS/API → SQLite). El sleep del Mac pausa el bucle.
#
#   chmod +x mac/minar.command
#   ./mac/minar.command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
MINE_LOG="$LOG_DIR/mac-mine.log"
PID_FILE="$LOG_DIR/mac-mine.pid"

mkdir -p "$LOG_DIR"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "No hay .venv de macOS. Ejecuta primero Instalar-y-abrir.command"
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

if [ -f "$PID_FILE" ]; then
  old="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${old}" ] && kill -0 "$old" 2>/dev/null; then
    echo "El minero ya corre (PID $old). Log: $MINE_LOG"
    exit 0
  fi
fi

export TNB_DEMO_SEED="${TNB_DEMO_SEED:-0}"
export TNB_FAST="${TNB_FAST:-0}"

echo "----- $(date '+%Y-%m-%d %H:%M:%S') mine_loop -----" >> "$MINE_LOG"
nohup python "$ROOT/mine_loop.py" >> "$MINE_LOG" 2>&1 &
echo $! > "$PID_FILE"

echo "Minero en segundo plano (PID $(cat "$PID_FILE"))."
echo "Log: $MINE_LOG"
echo "El sleep/hibernación pausa la minería. Para parar: mac/detener.command"
echo "Un ciclo no iguala los ~160 de Windows. Copia tnb.db: mac/copiar-datos.md"
