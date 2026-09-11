"""Snippets reales de fichas oficiales (cache 24 h). No usa homepages como prueba."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import DATA_DIR, ensure_paths  # noqa: E402

ensure_paths()

from access import USER_AGENT  # noqa: E402
from html_fetcher import extract_main_text  # noqa: E402

CACHE_DIR = DATA_DIR / "cache" / "evidence"
TTL_SECONDS = 24 * 3600
TIMEOUT = 8.0
GENERIC_PATHS = {"/", "/en", "/es", "/animal-health/en", "/animal-health/en/"}

# Páginas de enfermedad (no homes). Si 404, se omiten.
DISEASE_PAGES: dict[str, list[dict[str, str]]] = {
    "gripe_aviar": [
        {
            "url": "https://www.woah.org/en/disease/avian-influenza/",
            "title": "WOAH — influenza aviar",
        },
        {
            "url": "https://www.cdc.gov/bird-flu/index.html",
            "title": "CDC — bird flu",
        },
        {
            "url": "https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza",
            "title": "USDA APHIS — avian influenza",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production & health",
        },
        {
            "url": "https://www.gob.mx/senasica/acciones-y-programas/influenza-aviar",
            "title": "SENASICA — influenza aviar",
        },
    ],
    "gusano_barrenador": [
        {
            "url": "https://www.woah.org/en/disease/new-world-screwworm/",
            "title": "WOAH — New World screwworm",
        },
        {
            "url": "https://www.aphis.usda.gov/livestock-poultry-disease/cattle/ticks/screwworm",
            "title": "USDA APHIS — screwworm",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production & health",
        },
        {
            "url": "https://www.gob.mx/senasica/acciones-y-programas/campana-nacional-contra-el-gusano-barrenador-del-ganado",
            "title": "SENASICA — campaña barrenador",
        },
    ],
    "fiebre_porcina_clasica": [
        {
            "url": "https://www.woah.org/en/disease/classical-swine-fever/",
            "title": "WOAH — classical swine fever",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production & health",
        },
        {
            "url": "https://www.gob.mx/senasica/acciones-y-programas/peste-porcina-clasica",
            "title": "SENASICA — peste porcina clásica",
        },
    ],
}

OFFICIAL_HOSTS = {
    "woah.org",
    "www.woah.org",
    "who.int",
    "www.who.int",
    "fao.org",
    "www.fao.org",
    "cdc.gov",
    "www.cdc.gov",
    "gob.mx",
    "www.gob.mx",
    "usda.gov",
    "www.usda.gov",
    "aphis.usda.gov",
    "www.aphis.usda.gov",
    "paho.org",
    "www.paho.org",
}


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{digest}.json"


def is_generic_homepage(url: str) -> bool:
    parsed = urlparse(url or "")
    path = (parsed.path or "/").rstrip("/") or "/"
    if path in {"/", ""}:
        return True
    if path in GENERIC_PATHS:
        return True
    host = (parsed.hostname or "").lower()
    if host.endswith("gob.mx") and path in {"/senasica", "/senasica/"}:
        return True
    if host.endswith("usda.gov") and path in {"/", ""}:
        return True
    return False


def is_official_url(url: str) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS)


def _read_cache(url: str) -> dict[str, Any] | None:
    path = _cache_path(url)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    fetched = float(data.get("fetched_at") or 0)
    if _now() - fetched > TTL_SECONDS:
        return None
    return data


def _write_cache(payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(str(payload.get("url") or ""))
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def fetch_official_page(url: str, title: str = "") -> dict[str, Any] | None:
    """GET de una ficha oficial. Omite 404 y homepages genéricas sin cuerpo útil."""
    if not url or is_generic_homepage(url):
        return None
    cached = _read_cache(url)
    if cached:
        if cached.get("status") == 404 or cached.get("ok") is False:
            return None
        if (cached.get("snippet") or "").strip():
            return cached
        return None
    if os.environ.get("TNB_FAST", "0") == "1":
        return None
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(url)
            status = response.status_code
            if status == 404:
                _write_cache({"url": url, "ok": False, "status": 404, "fetched_at": _now(), "snippet": ""})
                return None
            response.raise_for_status()
            extracted = extract_main_text(response.text, base_url=str(response.url))
            snippet = (extracted.get("text") or "")[:1200]
            payload = {
                "url": str(response.url),
                "requested_url": url,
                "ok": True,
                "status": status,
                "title": title or extracted.get("title") or "",
                "snippet": snippet,
                "fetched_at": _now(),
            }
            _write_cache(payload)
            if len(snippet) < 80:
                return None
            return payload
    except Exception as exc:  # noqa: BLE001
        _write_cache(
            {
                "url": url,
                "ok": False,
                "status": 0,
                "error": str(exc)[:200],
                "fetched_at": _now(),
                "snippet": "",
            }
        )
        return None


def live_evidence_cards(diseases: list[str], limit: int = 4) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    seen_hosts: set[str] = set()
    for did in diseases or []:
        for item in DISEASE_PAGES.get(did, []):
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            host = (urlparse(url).hostname or "").lower()
            if host.startswith("www."):
                host = host[4:]
            if host in seen_hosts:
                continue
            page = fetch_official_page(url, title=item.get("title") or "")
            if not page:
                continue
            snippet = (page.get("snippet") or "").strip()
            if len(snippet) < 80:
                continue
            seen_hosts.add(host)
            cards.append(
                {
                    "url": page.get("url") or url,
                    "title": page.get("title") or item.get("title") or "",
                    "snippet": snippet[:900],
                    "tier": "official",
                    "live": "1",
                }
            )
            if len(cards) >= limit:
                return cards
    return cards
