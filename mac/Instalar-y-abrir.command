#!/bin/bash
# The NewsBreakers — instala dependencias y abre el observatorio (macOS).
#
# Doble clic en Finder, o desde Terminal:
#   chmod +x Instalar-y-abrir.command
#   ./Instalar-y-abrir.command
#
# Windows / Git en Windows no suelen marcar el bit +x.
# En el Mac, si Finder no lo abre:
#   chmod +x mac/Instalar-y-abrir.command mac/detener.command mac/minar.command mac/minar-ya.command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

API_PORT=8010
WEB_PORT=5173
API_URL="http://127.0.0.1:${API_PORT}"
WEB_URL="http://127.0.0.1:${WEB_PORT}/#/"
LOG_DIR="$ROOT/logs"
API_LOG="$LOG_DIR/mac-api.log"
WEB_LOG="$LOG_DIR/mac-web.log"

mkdir -p "$LOG_DIR"

echo "=== The NewsBreakers — observatorio (Mac) ==="
echo "Repo: $ROOT"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "No se encontró python3."
  echo "Instálalo con Homebrew:"
  echo "  brew install python"
  echo "Si no tienes brew: https://brew.sh"
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "No se encontró Node.js / npm."
  echo "Instálalos con Homebrew:"
  echo "  brew install node"
  echo "Si no tienes brew: https://brew.sh"
  exit 1
fi

echo "python3: $(python3 --version 2>&1)"
echo "node:    $(node --version)   npm: $(npm --version)"
echo ""

# Un .venv copiado desde Windows no sirve en macOS (falta bin/python).
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "Creando entorno virtual (.venv)..."
  if [ -d "$ROOT/.venv" ]; then
    echo "El .venv existente no es de macOS; se recrea."
    rm -rf "$ROOT/.venv"
  fi
  python3 -m venv "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
echo "Instalando dependencias Python..."
python -m pip install -r "$ROOT/requirements.txt"

echo "Instalando dependencias del dashboard..."
(
  cd "$ROOT/frontend"
  npm install
)

if [ ! -f "$ROOT/.env" ] && [ -f "$ROOT/.env.example" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Creado .env desde .env.example (sin secretos)."
fi

if [ -z "${TNB_DEMO_ROOT:-}" ]; then
  if [ -d "$ROOT/../Generador_Excel_Enfermedades" ]; then
    export TNB_DEMO_ROOT="$(cd "$ROOT/../Generador_Excel_Enfermedades" && pwd)"
  elif [ -d "$HOME/Desktop/Generador_Excel_Enfermedades" ]; then
    export TNB_DEMO_ROOT="$HOME/Desktop/Generador_Excel_Enfermedades"
  fi
fi

if [ -n "${TNB_DEMO_ROOT:-}" ]; then
  echo "TNB_DEMO_ROOT=$TNB_DEMO_ROOT"
else
  echo "Sin Generador Excel (opcional). Watchlist bundled."
fi
echo ""

port_listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if port_listening "$API_PORT"; then
  echo "API ya escucha en $API_URL"
else
  echo "Iniciando API en $API_URL ..."
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') uvicorn -----" >> "$API_LOG"
  nohup python -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT" \
    >> "$API_LOG" 2>&1 &
  disown || true
fi

if port_listening "$WEB_PORT"; then
  echo "Dashboard ya escucha en $WEB_URL"
else
  echo "Iniciando dashboard en $WEB_URL ..."
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') vite -----" >> "$WEB_LOG"
  nohup npm --prefix "$ROOT/frontend" run dev -- --host 127.0.0.1 --port "$WEB_PORT" \
    >> "$WEB_LOG" 2>&1 &
  disown || true
fi

echo ""
echo "Docker / MySQL no hace falta para abrir el observatorio (usa SQLite)."
echo "Opcional, warehouse MySQL desde la raíz del repo:"
echo "  cd \"$ROOT\" && docker compose up -d mysql"
echo ""

ARTICLES=0
if [ -f "$ROOT/data/processed/tnb.db" ]; then
  ARTICLES="$(python -c "import sqlite3; print(sqlite3.connect('data/processed/tnb.db').execute('select count(*) from articles').fetchone()[0])" 2>/dev/null || echo 0)"
fi
echo "Artículos en SQLite local: $ARTICLES"
if [ "${ARTICLES:-0}" -lt 50 ] 2>/dev/null; then
  echo ""
  echo "SQLite local tiene pocas notas. Tras git pull debería haber ~160."
  echo "  1) Para (detener.command) → git pull → vuelve a abrir este script"
  echo "  2) Guía: mac/copiar-datos.md"
  echo "Para crecer ya: mac/minar-ya.command (varios ciclos, logs visibles)"
  echo ""
else
  echo "Para seguir creciendo (sin Generador Excel): mac/minar-ya.command"
fi

sleep 4
echo "Abriendo ventana de app (sin barra del navegador)..."
nohup python "$ROOT/desktop/open.py" --url "$WEB_URL" >> "$LOG_DIR/desktop.log" 2>&1 &
disown || true

echo "Observatorio: $WEB_URL"
echo "API:          $API_URL"
echo "Docs API:     ${API_URL}/docs"
echo "Logs:         $API_LOG"
echo "              $WEB_LOG"
echo ""
echo "Puedes cerrar esta ventana. Los servicios siguen en segundo plano."
echo "Para parar: doble clic en detener.command"
echo "Minería (esta noche, ver el contador subir): mac/minar-ya.command"
echo "Minería continua (primer plano):             mac/minar.command"
echo ""
