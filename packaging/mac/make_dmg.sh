#!/usr/bin/env bash
# Crea .app + .pkg + .dmg y deja la app en ~/Applications.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_NAME="NewsBreakers 2.59.54 a.m."
STAGE="$(mktemp -d /tmp/tnb-mac.XXXX)"
APP="$STAGE/${APP_NAME}.app"
USER_APPS="$HOME/Applications"
DESK="$HOME/Desktop"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$ROOT/dist" "$USER_APPS"

hdiutil detach "/Volumes/The NewsBreakers" -force >/dev/null 2>&1 || true

echo "Compilando interfaz…"
(
  cd "$ROOT/frontend"
  if [ ! -d node_modules ]; then npm install; fi
  VITE_API_URL= npm run build
)

ICON_PNG="$ROOT/branding/logo.png"
ICON_ICNS="$ROOT/branding/logo.icns"
if [ -f "$ICON_ICNS" ]; then
  cp "$ICON_ICNS" "$APP/Contents/Resources/AppIcon.icns"
elif [ -f "$ICON_PNG" ]; then
  ICON_DIR="$ROOT/packaging/mac/icon.iconset"
  rm -rf "$ICON_DIR"
  mkdir -p "$ICON_DIR"
  python3 - "$ICON_PNG" "$ICON_DIR" <<'PY'
import sys
from pathlib import Path
from PIL import Image
src = Image.open(sys.argv[1]).convert("RGBA")
out = Path(sys.argv[2])
side = min(src.size)
left = (src.size[0] - side) // 2
top = (src.size[1] - side) // 2
base = src.crop((left, top, left + side, top + side)).resize((1024, 1024), Image.Resampling.LANCZOS)
for s, name in [(16,"icon_16x16.png"),(32,"icon_16x16@2x.png"),(32,"icon_32x32.png"),
                (64,"icon_32x32@2x.png"),(128,"icon_128x128.png"),(256,"icon_128x128@2x.png"),
                (256,"icon_256x256.png"),(512,"icon_256x256@2x.png"),(512,"icon_512x512.png"),
                (1024,"icon_512x512@2x.png")]:
    base.resize((s, s), Image.Resampling.LANCZOS).save(out / name)
PY
  iconutil -c icns "$ICON_DIR" -o "$APP/Contents/Resources/AppIcon.icns" 2>/dev/null || true
fi

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>NewsBreakers 2.59.54 a.m.</string>
  <key>CFBundleDisplayName</key><string>NewsBreakers 2.59.54 a.m.</string>
  <key>CFBundleIdentifier</key><string>mx.newsbreakers.observatorio</string>
  <key>CFBundleVersion</key><string>2.59.54</string>
  <key>CFBundleShortVersionString</key><string>2.59.54</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>NewsBreakers</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST

cp "$ROOT/packaging/mac/setup.sh" "$APP/Contents/Resources/setup.sh"
chmod +x "$ROOT/packaging/mac/setup.sh" "$APP/Contents/Resources/setup.sh"
if ! clang -fobjc-arc -Os -mmacosx-version-min=12.0 \
  "$ROOT/packaging/mac/NewsBreakers.m" \
  -o "$APP/Contents/MacOS/NewsBreakers" \
  -framework Cocoa -framework WebKit; then
  echo "clang falló; usando el lanzador bash."
  cp "$ROOT/packaging/mac/launch.sh" "$APP/Contents/MacOS/NewsBreakers"
fi
chmod +x "$APP/Contents/MacOS/NewsBreakers"

rsync -a \
  --exclude '.git/' --exclude '.venv/' --exclude 'node_modules/' \
  --exclude 'frontend/node_modules/' --exclude 'logs/' \
  --exclude '/dist/' --exclude '.pytest_cache/' --exclude '__pycache__/' \
  --exclude '.env' --exclude 'data/license.key' \
  "$ROOT/" "$APP/Contents/Resources/framework/"

if [ ! -f "$APP/Contents/Resources/framework/frontend/dist/index.html" ]; then
  echo "Falta frontend/dist dentro del .app"
  exit 1
fi

cat > "$STAGE/INSTALAR.txt" <<'TXT'
NewsBreakers 2.59.54 a.m.

1. Arrastra la app a la carpeta Aplicaciones (el atajo de este disco).
2. Ábrela desde Aplicaciones, no desde este disco.
3. La primera vez tarda un minuto (prepara Python del usuario).
4. Si macOS dice que no se puede abrir: clic derecho → Abrir.

También hay un .pkg en el Escritorio: doble clic e Instalar.
TXT
ln -s /Applications "$STAGE/Aplicaciones"

osascript -e 'tell application "NewsBreakers 2.59.54 a.m." to quit' >/dev/null 2>&1 || true
osascript -e 'tell application "The NewsBreakers" to quit' >/dev/null 2>&1 || true
osascript -e 'tell application "NewsBreakers" to quit' >/dev/null 2>&1 || true
sleep 1

install_user_app() {
  local dest="$1"
  rm -rf "$dest"
  ditto "$APP" "$dest"
  xattr -cr "$dest" 2>/dev/null || true
}

if [ -w "$USER_APPS" ] && { [ ! -e "$USER_APPS/${APP_NAME}.app" ] || [ -w "$USER_APPS/${APP_NAME}.app" ]; }; then
  install_user_app "$USER_APPS/${APP_NAME}.app" || true
fi
install_user_app "$DESK/${APP_NAME}.app"

PKGROOT="$(mktemp -d /tmp/tnb-pkg.XXXX)"
mkdir -p "$PKGROOT/Applications"
cp -R "$APP" "$PKGROOT/Applications/${APP_NAME}.app"
pkgbuild --identifier mx.newsbreakers.observatorio --version 2.59.54 \
  --install-location / --root "$PKGROOT" \
  "$DESK/NewsBreakers-2.59.54.pkg" >/tmp/tnb-pkg.log
cp "$DESK/NewsBreakers-2.59.54.pkg" "$ROOT/dist/NewsBreakers-2.59.54.pkg"
rm -rf "$PKGROOT"

rm -f "$DESK/NewsBreakers-2.59.54.dmg" "$ROOT/dist/NewsBreakers-2.59.54.dmg"
hdiutil create -volname "NewsBreakers 2.59.54 a.m." -srcfolder "$STAGE" -ov -format UDZO "$DESK/NewsBreakers-2.59.54.dmg" >/tmp/tnb-dmg.log
cp "$DESK/NewsBreakers-2.59.54.dmg" "$ROOT/dist/NewsBreakers-2.59.54.dmg"
rm -rf "$STAGE"

echo "App:     $DESK/${APP_NAME}.app"
echo "Paquete: $DESK/NewsBreakers-2.59.54.pkg"
echo "Disco:   $DESK/NewsBreakers-2.59.54.dmg"
open "$DESK/${APP_NAME}.app" || true
