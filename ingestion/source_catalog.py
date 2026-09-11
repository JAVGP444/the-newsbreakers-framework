"""Catálogo de fuentes (watchlist). No scrapeamos todo Internet.

Carga `sources/catalog.yaml` (semilla de datos/source_registry.yaml),
fusiona RSS de `rss_overrides.yaml` y calcula next_check / backoff.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

CATALOG_PATH = Path(__file__).resolve().parent / "sources" / "catalog.yaml"
OVERRIDES_PATH = Path(__file__).resolve().parent / "sources" / "rss_overrides.yaml"

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import SOURCE_REGISTRY  # noqa: E402

LEGACY_DB = SOURCE_REGISTRY

PRIORITY_MINUTES = {
    "critical": 15,
    "high": 30,
    "normal": 60,
    "low": 360,
    "scientific": 720,
}

ACCESS_ORDER = ("api", "rss", "scrape")
RETRY_DELAYS = (timedelta(seconds=30), timedelta(minutes=2))


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_overrides() -> dict[str, Any]:
    if not OVERRIDES_PATH.is_file():
        return {}
    return yaml.safe_load(OVERRIDES_PATH.read_text(encoding="utf-8")) or {}


def load_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    data = yaml.safe_load((path or CATALOG_PATH).read_text(encoding="utf-8")) or {}
    sources = list(data.get("sources") or [])
    overrides = _load_overrides()
    rss_by_domain = {str(k).lower(): v for k, v in (overrides.get("rss_by_domain") or {}).items()}
    by_id: dict[str, dict[str, Any]] = {}
    for source in sources:
        domain = str(source.get("domain") or "").lower()
        if domain in rss_by_domain:
            source["rss_url"] = rss_by_domain[domain]
        if source.get("rss_url") and source.get("access_method") == "scrape":
            source["access_method"] = "rss"
            source["scraper_type"] = "none"
        source.setdefault("parser_version", "parser_v1")
        source.setdefault("frequency_minutes", frequency_minutes(source))
        source.setdefault("last_checked", None)
        source.setdefault("next_check", None)
        source.setdefault("last_error", None)
        by_id[source["source_id"]] = source
    for extra in overrides.get("extra_sources") or []:
        if not isinstance(extra, dict) or not extra.get("source_id"):
            continue
        sid = extra["source_id"]
        if sid not in by_id:
            extra.setdefault("parser_version", "parser_v1")
            extra.setdefault("active", True)
            by_id[sid] = extra
    return list(by_id.values())


def load_catalog_meta(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or CATALOG_PATH).read_text(encoding="utf-8")) or {}


def active_sources(path: Path | None = None) -> list[dict[str, Any]]:
    return [s for s in load_catalog(path) if s.get("active", True)]


def get_source(source_id: str, path: Path | None = None) -> dict[str, Any] | None:
    for source in load_catalog(path):
        if source.get("source_id") == source_id:
            return source
    return None


def frequency_minutes(source: dict[str, Any]) -> int:
    if source.get("frequency_minutes"):
        return int(source["frequency_minutes"])
    return PRIORITY_MINUTES.get(str(source.get("priority") or "normal"), 60)


def select_access_method(source: dict[str, Any]) -> str:
    """Jerarquía: API si hay endpoint/agregador → RSS si hay url → scrape (MVP: diferido)."""
    declared = str(source.get("access_method") or "").lower()
    if declared == "api" or source.get("api_url") or (
        source.get("type") == "aggregator" and not source.get("rss_url")
    ):
        return "api"
    if source.get("rss_url"):
        return "rss"
    if declared in ACCESS_ORDER:
        return declared
    return "scrape"


def next_check(source: dict[str, Any], now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    stored = _parse_dt(source.get("next_check"))
    if stored:
        return stored
    last = _parse_dt(source.get("last_checked"))
    if not last:
        return now
    return last + timedelta(minutes=frequency_minutes(source))


def backoff_next_check(consecutive_failures: int, now: datetime | None = None) -> datetime:
    """1er fallo → +30s; 2º → +2m; 3er fallo → frequency (se deja de reintentar en este ciclo)."""
    now = now or datetime.now(timezone.utc)
    if consecutive_failures <= 1:
        return now + RETRY_DELAYS[0]
    if consecutive_failures == 2:
        return now + RETRY_DELAYS[1]
    return now + timedelta(hours=6)


def is_due(source: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return now >= next_check(source, now=now)


def merge_runtime(source: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(source)
    if not row:
        return merged
    for key in ("last_checked", "next_check", "last_error", "consecutive_failures", "last_success"):
        if row.get(key) is not None:
            merged[key] = row[key]
    return merged


def sources_due(
    sources: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
    methods: tuple[str, ...] = ("api", "rss"),
) -> list[dict[str, Any]]:
    """Fuentes pendientes. MVP: api/rss. scrape se lista aparte para log deferred."""
    now = now or datetime.now(timezone.utc)
    rows = sources if sources is not None else active_sources()
    due: list[dict[str, Any]] = []
    for source in rows:
        if not source.get("active", True):
            continue
        if select_access_method(source) not in methods:
            continue
        if is_due(source, now=now):
            due.append(source)
    due.sort(key=lambda s: (frequency_minutes(s), s.get("source_id") or ""))
    return due


def legacy_confidence(domain: str) -> int | None:
    if not LEGACY_DB.exists():
        return None
    data = yaml.safe_load(LEGACY_DB.read_text(encoding="utf-8")) or {}
    needle = domain.lower()
    categories = data.get("categories") or {}
    for cat_body in categories.values():
        if not isinstance(cat_body, dict):
            continue
        for item in cat_body.get("sources") or []:
            if not isinstance(item, dict):
                continue
            domains = [str(d).lower() for d in (item.get("domains") or [])]
            if needle in domains or needle in str(item.get("id") or "").lower():
                return int(item.get("priority") or 0) * 10
    return None
