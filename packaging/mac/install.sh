#!/usr/bin/env bash
# Instala el .app en /Applications (Mac).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/dist/NewsBreakers.app"
if [ ! -d "$APP" ]; then
  echo "Primero: python packaging/build.py"
  exit 1
fi
rm -rf /Applications/NewsBreakers.app
cp -R "$APP" /Applications/NewsBreakers.app
echo "Instalado: /Applications/NewsBreakers.app"
open /Applications/NewsBreakers.app
