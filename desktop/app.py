"""App instalada: API + ventana. Sin navegador.

  python desktop/app.py
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

if getattr(sys, "frozen", False):
    if os.name == "nt":
        _home = Path(os.environ.get("APPDATA") or Path.home()) / "TheNewsBreakers"
    else:
        _home = Path.home() / "Library/Application Support/TheNewsBreakers"
    os.environ.setdefault("TNB_HOME", str(_home))
    _meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    if str(_meipass) not in sys.path:
        sys.path.insert(0, str(_meipass))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.paths import seed_writable_home  # noqa: E402

seed_writable_home()
os.chdir(os.environ.get("TNB_HOME") or str(ROOT))
HOST = os.environ.get("GATEWAY_HOST", "127.0.0.1")


def _ours(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/health", timeout=0.8) as res:
            return res.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _pick_port(preferred: int) -> tuple[int, bool]:
    if _ours(preferred):
        return preferred, True
    sock = socket.socket()
    try:
        sock.bind((HOST, preferred))
        sock.close()
        return preferred, False
    except OSError:
        sock.close()
    sock = socket.socket()
    sock.bind((HOST, 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port, False


def _serve(port: int) -> None:
    import uvicorn

    uvicorn.run("api.main:app", host=HOST, port=port, log_level="warning")


def _wait(port: int, seconds: int = 40) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if _ours(port):
            return True
        time.sleep(0.3)
    return False


def main() -> int:
    serve_only = "--serve" in sys.argv or os.environ.get("TNB_SERVE") == "1"
    preferred = int(os.environ.get("GATEWAY_PORT") or 8010)
    if serve_only:
        already = _ours(preferred)
        if already:
            while True:
                time.sleep(60)
            return 0
        _serve(preferred)
        return 0
    port, already = _pick_port(preferred)
    url = f"http://{HOST}:{port}/#/"
    if not already:
        threading.Thread(target=_serve, args=(port,), daemon=True).start()
        if not _wait(port):
            print("La API no arrancó.", file=sys.stderr)
            return 1
    try:
        import webview
    except ImportError:
        from desktop.open import open_chrome_app, open_fallback_browser

        if not open_chrome_app(url):
            open_fallback_browser(url)
        if not already:
            while True:
                time.sleep(60)
        return 0
    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    except Exception:
        pass
    window = webview.create_window("The NewsBreakers", url, width=1280, height=840, min_size=(880, 600))

    def _external(dest: str) -> bool:
        host = (urllib.parse.urlparse(dest).hostname or "").lower()
        if host in {"127.0.0.1", "localhost"}:
            return True
        webbrowser.open(dest)
        return False

    try:
        window.events.redirect += _external
    except Exception:
        pass
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
