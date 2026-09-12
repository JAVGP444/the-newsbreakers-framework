"""Dónde vive el código (bundle) y dónde se puede escribir (casa).

En desarrollo coinciden. El .exe de Windows escribe en %APPDATA%\\TheNewsBreakers.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def app_home() -> Path:
    env = (os.environ.get("TNB_HOME") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if getattr(sys, "frozen", False):
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA") or Path.home())
            return (base / "TheNewsBreakers").resolve()
        return (Path.home() / "Library/Application Support/TheNewsBreakers").resolve()
    return bundle_root()


def seats_db_path() -> Path:
    env = (os.environ.get("TNB_SEATS_PATH") or "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    path = app_home() / "data" / "accounts.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def seed_writable_home() -> Path:
    home = app_home()
    src = bundle_root()
    home.mkdir(parents=True, exist_ok=True)
    if home.resolve() == src.resolve():
        return home
    copies = (
        "data/processed/tnb.db",
        "frontend/dist",
        "config/diseases.yaml",
        "config/watchlist.yaml",
        "config/enfermedades_config.yaml",
        "ingestion/sources",
        "branding",
        "models/cnn",
        ".env.example",
    )
    for rel in copies:
        s = src / rel
        d = home / rel
        if not s.exists():
            continue
        if s.is_dir():
            if not d.exists():
                shutil.copytree(s, d)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists():
                shutil.copy2(s, d)
    (home / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (home / "storage" / "images").mkdir(parents=True, exist_ok=True)
    return home
