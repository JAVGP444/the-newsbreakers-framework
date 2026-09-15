"""Snippets reales de fichas oficiales (cache 24 h). No usa homepages como prueba."""
from __future__ import annotations

import hashlib
import json
import os
import re
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

CACHE_DIR = DATA_DIR / "cache" / "evidence_v2"
TTL_SECONDS = 24 * 3600
TIMEOUT = 8.0
GENERIC_PATHS = {"/", "/en", "/es", "/animal-health/en", "/animal-health/en/"}
MAX_SNIPPET = 8000

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
    "tahc.texas.gov",
    "www.tahc.texas.gov",
    "canada.ca",
    "inspection.canada.ca",
    "copeg.org",
    "www.copeg.org",
    "senasa.gob.ar",
    "www.senasa.gob.ar",
}

# Boletines y tableros de brote, no la ficha de especie.
EVENT_PAGES: dict[str, list[dict[str, str]]] = {
    "gusano_barrenador": [
        {
            "url": "https://www.aphis.usda.gov/news/agency-announcements/usda-confirms-presence-new-world-screwworm-united-states",
            "title": "USDA — confirma NWS en EE.UU.",
        },
        {
            "url": "https://www.aphis.usda.gov/news/agency-announcements/usda-confirms-two-additional-cases-new-world-screwworm-united-states",
            "title": "USDA — casos adicionales NWS",
        },
        {
            "url": "https://www.aphis.usda.gov/news/agency-announcements/usda-continues-lead-coordinated-response-new-world-screwworm-new-case",
            "title": "USDA — respuesta NWS / La Salle",
        },
        {
            "url": "https://www.aphis.usda.gov/animals/animal-health/livestock-and-poultry-disease/current-status/us-confirmed-cases-new-world",
            "title": "USDA — detecciones confirmadas NWS",
        },
        {
            "url": "https://www.gob.mx/senasica/acciones-y-programas/campana-nacional-contra-el-gusano-barrenador-del-ganado",
            "title": "SENASICA — campaña barrenador",
        },
    ],
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
    ],
    "fiebre_porcina_clasica": [
        {
            "url": "https://www.woah.org/en/disease/classical-swine-fever/",
            "title": "WOAH — classical swine fever",
        },
    ],
}

NEWS_FEEDS: dict[str, list[str]] = {
    "gusano_barrenador": ["https://www.aphis.usda.gov/rss/news.xml"],
    "gripe_aviar": ["https://www.aphis.usda.gov/rss/news.xml"],
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
            snippet = (extracted.get("text") or "")[:MAX_SNIPPET]
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


def _rss_items(feed_url: str) -> list[dict[str, str]]:
    cached = _read_cache(feed_url)
    xml = ""
    if cached and cached.get("xml"):
        xml = str(cached.get("xml") or "")
    elif os.environ.get("TNB_FAST", "0") != "1":
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
                response = client.get(feed_url)
                response.raise_for_status()
                xml = response.text[:200000]
                _write_cache({"url": feed_url, "ok": True, "xml": xml, "fetched_at": _now(), "snippet": xml[:200]})
        except Exception:
            return []
    items: list[dict[str, str]] = []

    def _strip(raw: str) -> str:
        text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", raw or "", flags=re.S)
        return re.sub(r"<[^>]+>", " ", text)

    for block in re.findall(r"<item\b[^>]*>(.*?)</item>", xml, flags=re.I | re.S)[:30]:
        title = re.search(r"<title[^>]*>(.*?)</title>", block, flags=re.I | re.S)
        link = re.search(r"<link[^>]*>(.*?)</link>", block, flags=re.I | re.S)
        desc = re.search(r"<description[^>]*>(.*?)</description>", block, flags=re.I | re.S)
        items.append(
            {
                "title": _strip(title.group(1) if title else "").strip(),
                "url": _strip(link.group(1) if link else "").strip(),
                "snippet": _strip(desc.group(1) if desc else "").strip()[:900],
            }
        )
    return items


def live_event_cards(diseases: list[str], claim_text: str, limit: int = 4) -> list[dict[str, str]]:
    """Párrafos de boletines que hablan del hecho de la nota, no de la especie."""
    from database.event_facts import compare_facts, pick_paragraph

    scored: list[tuple[int, dict[str, str]]] = []
    seen: set[str] = set()
    claim = claim_text or ""
    for did in diseases or []:
        for item in EVENT_PAGES.get(did, []):
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            page = fetch_official_page(url, title=item.get("title") or "")
            if not page:
                continue
            body = (page.get("snippet") or "").strip()
            para, score = pick_paragraph(claim, body)
            snippet = para or body[:500]
            compared = compare_facts(claim, snippet)
            if compared["status"] not in {"hit", "partial"} and score < 3:
                continue
            scored.append(
                (
                    score + (5 if compared["status"] == "hit" else 2 if compared["status"] == "partial" else 0),
                    {
                        "url": page.get("url") or url,
                        "title": page.get("title") or item.get("title") or "",
                        "snippet": snippet[:900],
                        "tier": "official",
                        "live": "1",
                        "event": "1",
                    },
                )
            )
        for feed in NEWS_FEEDS.get(did, []):
            for rss in _rss_items(feed):
                url = rss.get("url") or ""
                if not url or url in seen or not is_official_url(url):
                    continue
                blob = f"{rss.get('title') or ''} {rss.get('snippet') or ''}"
                para, score = pick_paragraph(claim, blob)
                snippet = para or (rss.get("snippet") or rss.get("title") or "")
                compared = compare_facts(claim, snippet)
                if compared["status"] not in {"hit", "partial"} and score < 3:
                    continue
                seen.add(url)
                scored.append(
                    (
                        score + (5 if compared["status"] == "hit" else 2),
                        {
                            "url": url,
                            "title": rss.get("title") or "",
                            "snippet": snippet[:900],
                            "tier": "official",
                            "live": "1",
                            "event": "1",
                        },
                    )
                )
    scored.sort(key=lambda x: -x[0])
    return [card for _, card in scored[:limit]]
