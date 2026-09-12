"""Arma el instalador del SO donde corres este script.

Mac → NewsBreakers.app + .dmg
Windows → NewsBreakers.exe (Inno Setup hace el Setup.exe si está instalado)
Linux → directorio + .desktop (copiar a /usr/local)

  cd pack raíz
  python packaging/build.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=kw.get("cwd", ROOT), env={**os.environ, **kw.get("env", {})})


def build_ui() -> None:
    frontend = ROOT / "frontend"
    env = {**os.environ, "VITE_API_URL": ""}
    _run(["npm", "install"], cwd=frontend)
    _run(["npm", "run", "build"], cwd=frontend, env=env)
    dist = frontend / "dist" / "index.html"
    if not dist.is_file():
        raise SystemExit("frontend/dist no se generó")


def pyinstaller() -> None:
    _run([sys.executable, "-m", "pip", "install", "pyinstaller", "pywebview"])
    spec = ROOT / "packaging" / "NewsBreakers.spec"
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)])


def mac_dmg() -> None:
    app = ROOT / "dist" / "NewsBreakers.app"
    if not app.is_dir():
        print("No hay .app (¿no es macOS?)")
        return
    dmg = ROOT / "dist" / "NewsBreakers.dmg"
    if dmg.exists():
        dmg.unlink()
    _run(["hdiutil", "create", "-volname", "NewsBreakers", "-srcfolder", str(app), "-ov", "-format", "UDZO", str(dmg)])
    print("Instalador Mac:", dmg)
    print("Arrastra NewsBreakers.app a /Applications")


def windows_note() -> None:
    exe_dir = ROOT / "dist" / "NewsBreakers"
    print("Windows: dist/NewsBreakers/NewsBreakers.exe")
    iss = ROOT / "packaging" / "windows" / "setup.iss"
    print("Setup.exe: instala Inno Setup y compila", iss)


def linux_desktop() -> None:
    src = ROOT / "packaging" / "linux" / "newsbreakers.desktop"
    dest = ROOT / "dist" / "newsbreakers.desktop"
    if src.is_file():
        shutil.copy(src, dest)
    logo = ROOT / "packaging" / "linux" / "newsbreakers.png"
    if logo.is_file():
        shutil.copy(logo, ROOT / "dist" / "newsbreakers.png")
    print("Linux: copia dist/NewsBreakers a /opt/newsbreakers y el .desktop a ~/.local/share/applications/")


def main() -> int:
    build_ui()
    pyinstaller()
    if sys.platform == "darwin":
        mac_dmg()
    elif os.name == "nt":
        windows_note()
    else:
        linux_desktop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
