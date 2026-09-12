"""Adaptador API — GDELT DOC 2.0 vía httpx (sin el verificador viejo)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from access import USER_AGENT, polite_delay, resolve_access
from normalize import UniversalContent, to_universal

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY = '("avian influenza" OR H5N1 OR HPAI OR screwworm OR "classical swine fever" OR "gusano barrenador" OR "gripe aviar" OR SENASICA OR WOAH)'


def _gdelt_max(explicit: int | None = None) -> int:
    from config.license import COMMUNITY_CAPS, apply_cap

    if explicit is not None:
        raw = max(1, min(250, int(explicit)))
    else:
        try:
            raw = max(1, min(250, int(os.environ.get("TNB_GDELT_MAX", "75"))))
        except ValueError:
            raw = 75
    return apply_cap("mine", raw, COMMUNITY_CAPS["gdelt_max"])


def _lookback_days() -> int:
    try:
        return max(1, min(90, int(os.environ.get("TNB_GDELT_LOOKBACK_DAYS", "21"))))
    except ValueError:
        return 21


def _windows_per_cycle() -> int:
    from config.license import COMMUNITY_CAPS, apply_cap

    try:
        raw = max(1, min(8, int(os.environ.get("TNB_GDELT_WINDOWS", "4"))))
    except ValueError:
        raw = 4
    return apply_cap("mine", raw, COMMUNITY_CAPS["gdelt_windows"])


def gdelt_query_windows(
    now: datetime | None = None,
    offset_days: int = 0,
    lookback_days: int | None = None,
    windows: int | None = None,
    window_hours: int = 24,
) -> list[tuple[datetime, datetime]]:
    """Ventanas históricas para no repetir siempre los mismos 40 artículos recientes."""
    now = now or datetime.now(timezone.utc)
    lookback = lookback_days if lookback_days is not None else _lookback_days()
    n = windows if windows is not None else _windows_per_cycle()
    offset = offset_days % max(1, lookback)
    out: list[tuple[datetime, datetime]] = []
    for i in range(n):
        end = now - timedelta(days=offset, hours=i * window_hours)
        start = end - timedelta(hours=window_hours)
        if start < now - timedelta(days=lookback):
            break
        out.append((start, end))
    return out


def _fmt_gdelt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def fetch_gdelt(
    max_records: int | None = None,
    timeout: float = 25.0,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    timespan: str | None = None,
) -> list[dict[str, Any]]:
    max_records = _gdelt_max(max_records)
    params: dict[str, str] = {
        "query": GDELT_QUERY,
        "mode": "ArtList",
        "maxrecords": str(max_records),
        "format": "json",
        "sort": "datedesc",
    }
    if start and end:
        params["startdatetime"] = _fmt_gdelt(start)
        params["enddatetime"] = _fmt_gdelt(end)
    elif timespan:
        params["timespan"] = timespan
    url = f"{GDELT_URL}?{urlencode(params)}"
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    return list(data.get("articles") or [])


def _article_to_item(source: dict[str, Any], article: dict[str, Any]) -> UniversalContent | None:
    url = article.get("url") or ""
    if not url:
        return None
    title = (article.get("title") or "").strip()
    seen = article.get("seendate") or ""
    return to_universal(
        source_id=source.get("source_id") or "SRC109",
        url=url,
        title=title,
        text=title,
        published_at=seen or None,
        language=article.get("language") or "und",
        raw_format="api",
    )


def fetch_source_api(source: dict[str, Any], max_records: int | None = None) -> list[UniversalContent]:
    if resolve_access(source) != "api":
        return []
    domain = str(source.get("domain") or "")
    if "gdelt" not in domain:
        return []
    polite_delay(source)
    seen: set[str] = set()
    items: list[UniversalContent] = []

    def _absorb(articles: list[dict[str, Any]]) -> None:
        for article in articles:
            item = _article_to_item(source, article)
            if not item or item.url in seen:
                continue
            seen.add(item.url)
            items.append(item)

    # Siempre la ventana reciente (notas nuevas) + ventanas históricas (crecimiento).
    _absorb(fetch_gdelt(max_records=max_records, timespan="2d"))
    offset = 0
    try:
        from database.mine_state import read_mine_state

        offset = int((read_mine_state() or {}).get("gdelt_offset_days") or 0)
    except Exception:
        offset = 0
    for start, end in gdelt_query_windows(offset_days=offset):
        try:
            _absorb(fetch_gdelt(max_records=max_records, start=start, end=end))
        except Exception:
            continue
    try:
        from database.mine_state import read_mine_state, write_mine_state

        lookback = _lookback_days()
        nxt = (offset + _windows_per_cycle()) % lookback
        write_mine_state({**read_mine_state(), "gdelt_offset_days": nxt})
    except Exception:
        pass
    from html_fetcher import enrich_rss_items

    return enrich_rss_items(items, source)
