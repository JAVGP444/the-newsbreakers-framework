#!/usr/bin/env bash
# Instala el .app en /Applications (Mac).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_NAME="NewsBreakers 2.59.54 a.m."
APP="$ROOT/dist/${APP_NAME}.app"
if [ ! -d "$APP" ]; then
  echo "Primero: bash packaging/mac/make_dmg.sh"
  exit 1
fi
rm -rf "/Applications/${APP_NAME}.app"
cp -R "$APP" "/Applications/${APP_NAME}.app"
echo "Instalado: /Applications/${APP_NAME}.app"
open "/Applications/${APP_NAME}.app"
