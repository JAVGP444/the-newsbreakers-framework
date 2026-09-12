#!/bin/bash
# Varios ciclos SEGUIDOS (sin esperar 30 min) para ver el KPI subir esta noche.
#
#   chmod +x mac/minar-ya.command
#   ./mac/minar-ya.command
#
# Recorre TODA la watchlist RSS/API/HTML, TNB_FAST=0, sin semilla demo.
# Cada ciclo avanza ventanas GDELT históricas (no solo las mismas 26 URLs RSS).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
MINE_LOG="$LOG_DIR/mac-mine-ya.log"
PY="$ROOT/.venv/bin/python"
CYCLES="${TNB_BURST_CYCLES:-8}"

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
export TNB_FORCE_DUE=1
export TNB_MAX_SOURCES="${TNB_MAX_SOURCES:-250}"
export TNB_RSS_LIMIT="${TNB_RSS_LIMIT:-100}"
export TNB_RSS_PAGES="${TNB_RSS_PAGES:-3}"
export TNB_GDELT_MAX="${TNB_GDELT_MAX:-75}"
export TNB_GDELT_WINDOWS="${TNB_GDELT_WINDOWS:-4}"
export TNB_GDELT_LOOKBACK_DAYS="${TNB_GDELT_LOOKBACK_DAYS:-21}"
export TNB_HTML_LISTINGS="${TNB_HTML_LISTINGS:-1}"
export TNB_HTML_LISTING_SOURCES="${TNB_HTML_LISTING_SOURCES:-10}"
export TNB_HTML_FETCH_PER_SOURCE="${TNB_HTML_FETCH_PER_SOURCE:-8}"
export PYTHONUNBUFFERED=1

count_articles() {
  "$PY" -c "import sqlite3, pathlib; p=pathlib.Path('data/processed/tnb.db'); print(sqlite3.connect(p).execute('select count(*) from articles').fetchone()[0] if p.is_file() else 0)"
}

echo "=== The NewsBreakers — minar YA (Mac) ==="
echo "Repo:     $ROOT"
echo "Python:   $PY ($("$PY" --version 2>&1))"
echo "Ciclos:   $CYCLES seguidos (sin sleep de 30 min)"
echo "TNB_FAST=0  TNB_DEMO_SEED=0  TNB_FORCE_DUE=1  TNB_MAX_SOURCES=$TNB_MAX_SOURCES"
echo "Artículos ahora: $(count_articles)"
echo "Log: $MINE_LOG"
echo "Deja el Mac despierto. Ctrl+C cancela."
echo ""

echo "----- $(date '+%Y-%m-%d %H:%M:%S') minar-ya $CYCLES ciclos -----" >> "$MINE_LOG"

"$PY" -u "$ROOT/run_cycle.py" --force-due --cycles "$CYCLES" --max-sources "$TNB_MAX_SOURCES" 2>&1 | tee -a "$MINE_LOG"
status=${PIPESTATUS[0]}

echo ""
echo "Artículos después: $(count_articles)"
echo "Recarga http://127.0.0.1:5173/#/  (o vuelve a abrir Instalar-y-abrir.command)"
echo "YouTube/redes nuevas siguen necesitando claves API o el Generador Excel."
exit "$status"
