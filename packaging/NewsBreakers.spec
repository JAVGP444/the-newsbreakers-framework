# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]
datas = [
    (str(root / "frontend" / "dist"), "frontend/dist"),
    (str(root / "config"), "config"),
    (str(root / "data" / "processed" / "tnb.db"), "data/processed"),
    (str(root / "models" / "cnn"), "models/cnn"),
    (str(root / "ingestion" / "sources"), "ingestion/sources"),
]

a = Analysis(
    [str(root / "desktop" / "app.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=["uvicorn.logging", "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl", "config.paths", "config.accounts", "config.license"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NewsBreakers",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(root / "branding" / ("logo.icns" if sys.platform == "darwin" else "logo.ico")),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="NewsBreakers",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="NewsBreakers.app",
        icon=str(root / "branding" / "logo.icns"),
        bundle_identifier="mx.newsbreakers.observatorio",
    )

