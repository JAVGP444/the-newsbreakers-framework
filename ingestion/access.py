"""Jerarquía de adquisición y cortesía hacia las fuentes.

API → RSS → scrape (scrape es último recurso; en MVP se omite con log
"scrape deferred"). No crawler abierto.
"""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from source_catalog import select_access_method

PRIORITY_DELAY_SECONDS = {
    "critical": 1.0,
    "high": 2.0,
    "normal": 4.0,
    "low": 8.0,
    "scientific": 6.0,
}

USER_AGENT = "TheNewsBreakers/framework (+https://github.com/the-newsbreakers)"
SCRAPE_DEFERRED = "scrape deferred"


def resolve_access(source: dict[str, Any]) -> str:
    return select_access_method(source)


def delay_seconds(source: dict[str, Any]) -> float:
    base = float(PRIORITY_DELAY_SECONDS.get(str(source.get("priority") or "normal"), 4.0))
    if os.environ.get("TNB_FAST", "0") == "1":
        return max(0.05, base * float(os.environ.get("TNB_DELAY_SCALE", "0.05")))
    return base


def polite_delay(source: dict[str, Any]) -> None:
    seconds = delay_seconds(source)
    if seconds > 0:
        time.sleep(seconds)


def scrape_deferred_note(source: dict[str, Any]) -> str:
    return (
        f"{SCRAPE_DEFERRED}: {source.get('source_id')} "
        f"({source.get('name') or source.get('domain')}) — sin API ni RSS en MVP"
    )


_ROBOTS_CACHE: dict[str, RobotFileParser | None] = {}


def robots_allowed(url: str, user_agent: str = USER_AGENT, timeout: float = 8.0) -> bool:
    """Comprueba robots.txt con timeout. 404 → permitir. Error de red → denegar (fail-closed)."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin in _ROBOTS_CACHE:
        rp = _ROBOTS_CACHE[origin]
        if rp is None:
            return False
        return bool(rp.can_fetch(user_agent, url))
    robots_url = urljoin(origin, "/robots.txt")
    rp = RobotFileParser()
    try:
        import httpx

        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": user_agent}) as client:
            response = client.get(robots_url)
        if response.status_code == 404:
            rp.parse([])
            _ROBOTS_CACHE[origin] = rp
            return True
        if response.status_code >= 400:
            _ROBOTS_CACHE[origin] = None
            return False
        rp.parse(response.text.splitlines())
        _ROBOTS_CACHE[origin] = rp
        return bool(rp.can_fetch(user_agent, url))
    except Exception:
        _ROBOTS_CACHE[origin] = None
        return False
