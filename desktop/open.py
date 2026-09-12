"""Ventana de escritorio. Sin pestañas ni barra de URL.

  python desktop/open.py
  python desktop/open.py --url http://127.0.0.1:5174/#/
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = os.environ.get("TNB_WEB_URL", "http://127.0.0.1:5173/#/")
TITLE = "The NewsBreakers"


def _ready(url: str) -> bool:
    base = url.split("#", 1)[0].rstrip("/") or url
    try:
        urllib.request.urlopen(base, timeout=1.5)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_for(url: str, seconds: int = 40) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if _ready(url):
            return True
        time.sleep(0.4)
    return False


def _chrome() -> str | None:
    if sys.platform == "darwin":
        for app in (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ):
            if Path(app).is_file():
                return app
        return None
    if os.name == "nt":
        for name in ("msedge", "chrome", "chromium"):
            found = shutil.which(name)
            if found:
                return found
        return None
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def open_chrome_app(url: str) -> bool:
    binary = _chrome()
    if not binary:
        return False
    profile = ROOT / "logs" / "chrome-app"
    profile.mkdir(parents=True, exist_ok=True)
    args = [binary, f"--app={url}", f"--user-data-dir={profile}", "--new-window"]
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def open_webview(url: str) -> bool:
    try:
        import webview
    except ImportError:
        return False
    webview.create_window(
        TITLE,
        url,
        width=1280,
        height=840,
        min_size=(880, 600),
        confirm_close=False,
    )
    webview.start()
    return True


def open_fallback_browser(url: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
        return
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
        return
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, url])


def main() -> int:
    parser = argparse.ArgumentParser(description="Abrir The NewsBreakers como ventana")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--wait", type=int, default=40)
    args = parser.parse_args()
    url = args.url
    if not wait_for(url, args.wait):
        print(f"No respondió {url}", file=sys.stderr)
        return 1
    if open_webview(url):
        return 0
    if open_chrome_app(url):
        print("Ventana Chromium (--app). pip install pywebview para WebKit nativo.")
        return 0
    open_fallback_browser(url)
    print("Se abrió el navegador. Instala pywebview o Chrome para modo app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
