"""Genera catalog.yaml desde datos/source_registry.yaml del observatorio vigente.

No forma parte del runtime. Ejecutar desde the-newsbreakers-framework:

  python ingestion/sources/_generate_catalog.py

Lee Generador_Excel_Enfermedades/datos/source_registry.yaml
(no el YAML del verificador FastAPI+Next.js).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import PROJECT_ROOT, SOURCE_REGISTRY, ensure_paths  # noqa: E402

ensure_paths()

OUT_PATH = Path(__file__).resolve().parent / "catalog.yaml"

KNOWN_RSS = {
    "who.int": "https://www.who.int/rss-feeds/news-english.xml",
    "woah.org": "https://www.woah.org/en/rss/",
    "cdc.gov": "https://tools.cdc.gov/api/v2/resources/media/403372.rss",
    "fao.org": "https://www.fao.org/newsroom/rss/en",
    "paho.org": "https://www.paho.org/en/rss.xml",
    "usda.gov": "https://www.usda.gov/rss/latest-releases.xml",
}

CATEGORY_META = {
    "OFFICIAL": ("critical", "official", 15),
    "EPIDEMIOLOGICAL": ("high", "surveillance", 60),
    "AGRICULTURAL": ("high", "veterinary", 60),
    "NEWS": ("normal", "media", 120),
    "FORUM": ("low", "forum", 360),
    "SOCIAL": ("low", "social", 180),
    "YOUTUBE": ("low", "youtube", 180),
    "AGGREGATOR": ("normal", "media", 60),
    "RESEARCH": ("scientific", "research", 720),
    "FACT_CHECK": ("normal", "fact_check", 120),
    "GENOMIC": ("scientific", "research", 720),
    "OTHER": ("normal", "other", 180),
}


def _first_domain(item: dict) -> str:
    domains = item.get("domains") or []
    if isinstance(domains, list) and domains:
        return str(domains[0]).strip().lower()
    patterns = item.get("patterns") or []
    if isinstance(patterns, list) and patterns:
        return str(patterns[0]).strip().lower().split("/")[0]
    return ""


def _access(item: dict, rss: str | None) -> str:
    declared = str(item.get("access_method") or "").lower()
    if declared in {"api", "rss", "scrape", "web"}:
        if declared == "web":
            return "rss" if rss else "scrape"
        if declared == "rss" or rss:
            return "rss"
        return declared
    if rss:
        return "rss"
    return "scrape"


def _default_authority(item: dict, cat_key: str, category: str) -> str:
    raw = str(item.get("source_authority") or "").strip().upper()
    if raw in {"A", "B", "C", "D", "E", "F"}:
        return raw
    domain = _first_domain(item)
    official = ("woah.org", "who.int", "fao.org", "cdc.gov", "gob.mx", "usda.gov", "paho.org")
    if any(domain == d or domain.endswith("." + d) for d in official):
        return "A"
    cat = str(cat_key or "").upper()
    if cat in {"OFFICIAL"}:
        return "A"
    if cat in {"RESEARCH", "GENOMIC", "EPIDEMIOLOGICAL", "AGRICULTURAL", "FACT_CHECK"}:
        return "B"
    if category == "official":
        return "A"
    if category in {"research", "veterinary", "surveillance"}:
        return "B"
    if cat in {"YOUTUBE"} or category == "youtube":
        return "D"
    if cat in {"SOCIAL", "FORUM"} or category in {"social", "forum"}:
        return "E"
    if cat in {"NEWS", "AGGREGATOR"} or category == "media":
        return "C"
    return ""


def _language(item: dict) -> str:
    lang = item.get("source_language") or item.get("language")
    if lang:
        return str(lang).split(",")[0].strip()
    country = str(item.get("country") or item.get("source_country") or "").upper()
    if country in {"MX", "ES", "AR", "CL", "CO", "PE"}:
        return "es"
    return "und"


def main() -> None:
    if not SOURCE_REGISTRY.is_file():
        raise SystemExit(f"No existe el registro de fuentes: {SOURCE_REGISTRY}")

    raw = yaml.safe_load(SOURCE_REGISTRY.read_text(encoding="utf-8")) or {}
    categories = raw.get("categories") or {}
    seen: dict[str, dict] = {}
    order: list[str] = []

    for cat_key, cat_body in categories.items():
        if not isinstance(cat_body, dict):
            continue
        priority, category, freq = CATEGORY_META.get(str(cat_key), ("normal", "other", 180))
        sources = cat_body.get("sources") or []
        if not isinstance(sources, list):
            continue
        for item in sources:
            if not isinstance(item, dict):
                continue
            domain = _first_domain(item)
            if not domain or domain in seen:
                continue
            rss = (item.get("rss_url") or "").strip() or KNOWN_RSS.get(domain)
            seeds = item.get("seed_urls") or []
            base = ""
            if isinstance(seeds, list) and seeds:
                base = str(seeds[0])
            source = {
                "source_id": "",
                "name": item.get("name") or item.get("id") or domain,
                "domain": domain,
                "country": item.get("country") or item.get("source_country") or "INT",
                "language": _language(item),
                "type": item.get("source_type") or cat_key,
                "category": category,
                "priority": priority,
                "access_method": _access(item, rss),
                "rss_url": rss or None,
                "base_url": base or f"https://{domain}",
                "scraper_type": "none" if rss else "html",
                "parser_version": "parser_v1",
                "frequency_minutes": freq,
                "confidence": int(item.get("priority") or 0) * 10,
                "authority": _default_authority(item, str(cat_key), category),
                "diseases": item.get("diseases") or [],
                "legacy_section": str(cat_key),
                "registry_id": item.get("id") or "",
                "active": True,
            }
            seen[domain] = source
            order.append(domain)

    if "api.gdeltproject.org" not in seen:
        seen["api.gdeltproject.org"] = {
            "source_id": "",
            "name": "GDELT DOC 2.0",
            "domain": "api.gdeltproject.org",
            "country": "INT",
            "language": "multi",
            "type": "aggregator",
            "category": "media",
            "priority": "normal",
            "access_method": "api",
            "rss_url": None,
            "base_url": "https://api.gdeltproject.org",
            "scraper_type": "none",
            "parser_version": "parser_v1",
            "frequency_minutes": 60,
            "confidence": 80,
            "authority": "C",
            "diseases": [],
            "legacy_section": "gdelt",
            "registry_id": "gdelt",
            "active": True,
        }
        order.append("api.gdeltproject.org")

    sources = []
    for i, domain in enumerate(order, start=1):
        row = seen[domain]
        row["source_id"] = f"SRC{i:03d}"
        sources.append(row)

    doc = {
        "version": 1,
        "parser_default": "parser_v1",
        "notes": (
            "Watchlist — no scrapeamos todo Internet. "
            "Semilla: Generador_Excel_Enfermedades/datos/source_registry.yaml + GDELT. "
            "Jerarquía de acceso: api → rss → scrape. Fase 1 solo ejecuta api/rss."
        ),
        "access_hierarchy": ["api", "rss", "scrape"],
        "priority_minutes": {
            "critical": 15,
            "high": 30,
            "normal": 60,
            "low": 360,
            "scientific": 720,
        },
        "project_root": str(PROJECT_ROOT),
        "sources": sources,
    }

    header = (
        "# Watchlist operativa — The NewsBreakers (framework Fase 1)\n"
        "# Generado desde Generador_Excel_Enfermedades/datos/source_registry.yaml\n"
        "# Regenerar: python ingestion/sources/_generate_catalog.py\n"
        "# No scrapeamos “todo Internet”: solo estas fuentes, con API/RSS primero.\n\n"
    )
    OUT_PATH.write_text(
        header + yaml.dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"Wrote {len(sources)} sources to {OUT_PATH}")
    print(f"Semilla: {SOURCE_REGISTRY}")


if __name__ == "__main__":
    main()
