"""Adaptador API — GDELT DOC 2.0 vía httpx (sin el verificador viejo)."""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx

from access import USER_AGENT, polite_delay, resolve_access
from normalize import UniversalContent, to_universal

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY = '("avian influenza" OR H5N1 OR HPAI OR screwworm OR "classical swine fever" OR "gusano barrenador" OR "gripe aviar" OR SENASICA OR WOAH)'


def _gdelt_max(explicit: int | None = None) -> int:
    if explicit is not None:
        return max(1, min(75, int(explicit)))
    try:
        return max(1, min(75, int(os.environ.get("TNB_GDELT_MAX", "40"))))
    except ValueError:
        return 40


def fetch_gdelt(max_records: int | None = None, timeout: float = 25.0) -> list[dict[str, Any]]:
    max_records = _gdelt_max(max_records)
    params = {
        "query": GDELT_QUERY,
        "mode": "ArtList",
        "maxrecords": str(max_records),
        "format": "json",
        "sort": "datedesc",
    }
    url = f"{GDELT_URL}?{urlencode(params)}"
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    return list(data.get("articles") or [])


def fetch_source_api(source: dict[str, Any], max_records: int | None = None) -> list[UniversalContent]:
    if resolve_access(source) != "api":
        return []
    domain = str(source.get("domain") or "")
    if "gdelt" not in domain:
        return []
    polite_delay(source)
    articles = fetch_gdelt(max_records=max_records)
    items: list[UniversalContent] = []
    for article in articles:
        url = article.get("url") or ""
        if not url:
            continue
        items.append(
            to_universal(
                source_id=source.get("source_id") or "SRC109",
                url=url,
                title=article.get("title") or "",
                text=article.get("seendate") or f"Cobertura mediática — {article.get('domain', '')}",
                published_at=article.get("seendate") or None,
                language=article.get("language") or "und",
                raw_format="api",
            )
        )
    return items
