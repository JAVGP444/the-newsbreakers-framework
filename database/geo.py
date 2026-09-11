"""Países, centroides y resolución geográfica para el mapa del observatorio."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bootstrap import DATOS_DIR, SALIDA_DIR

COUNTRY_META: dict[str, dict[str, Any]] = {
    "MX": {"name": "México", "lat": 23.63, "lng": -102.55},
    "US": {"name": "Estados Unidos", "lat": 39.83, "lng": -98.58},
    "GT": {"name": "Guatemala", "lat": 15.78, "lng": -90.23},
    "BZ": {"name": "Belice", "lat": 17.19, "lng": -88.50},
    "HN": {"name": "Honduras", "lat": 15.20, "lng": -86.24},
    "SV": {"name": "El Salvador", "lat": 13.79, "lng": -88.90},
    "NI": {"name": "Nicaragua", "lat": 12.87, "lng": -85.21},
    "CR": {"name": "Costa Rica", "lat": 9.75, "lng": -83.75},
    "PA": {"name": "Panamá", "lat": 8.54, "lng": -80.78},
    "CO": {"name": "Colombia", "lat": 4.57, "lng": -74.30},
    "VE": {"name": "Venezuela", "lat": 6.42, "lng": -66.59},
    "BR": {"name": "Brasil", "lat": -14.24, "lng": -51.93},
    "AR": {"name": "Argentina", "lat": -38.42, "lng": -63.62},
    "CL": {"name": "Chile", "lat": -35.68, "lng": -71.54},
    "PE": {"name": "Perú", "lat": -9.19, "lng": -75.02},
    "EC": {"name": "Ecuador", "lat": -1.83, "lng": -78.18},
    "BO": {"name": "Bolivia", "lat": -16.29, "lng": -63.59},
    "UY": {"name": "Uruguay", "lat": -32.52, "lng": -55.77},
    "PY": {"name": "Paraguay", "lat": -23.44, "lng": -58.44},
    "CU": {"name": "Cuba", "lat": 21.52, "lng": -77.78},
    "DO": {"name": "República Dominicana", "lat": 18.74, "lng": -70.16},
    "ES": {"name": "España", "lat": 40.46, "lng": -3.75},
    "FR": {"name": "Francia", "lat": 46.23, "lng": 2.21},
    "DE": {"name": "Alemania", "lat": 51.17, "lng": 10.45},
    "GB": {"name": "Reino Unido", "lat": 55.38, "lng": -3.44},
    "IT": {"name": "Italia", "lat": 41.87, "lng": 12.57},
    "NL": {"name": "Países Bajos", "lat": 52.13, "lng": 5.29},
    "CH": {"name": "Suiza", "lat": 46.82, "lng": 8.23},
    "CN": {"name": "China", "lat": 35.86, "lng": 104.20},
    "JP": {"name": "Japón", "lat": 36.20, "lng": 138.25},
    "KR": {"name": "Corea del Sur", "lat": 35.91, "lng": 127.77},
    "IN": {"name": "India", "lat": 20.59, "lng": 78.96},
    "AU": {"name": "Australia", "lat": -25.27, "lng": 133.78},
    "NZ": {"name": "Nueva Zelanda", "lat": -40.90, "lng": 174.89},
    "ZA": {"name": "Sudáfrica", "lat": -30.56, "lng": 22.94},
    "EG": {"name": "Egipto", "lat": 26.82, "lng": 30.80},
    "NG": {"name": "Nigeria", "lat": 9.08, "lng": 8.68},
    "CA": {"name": "Canadá", "lat": 56.13, "lng": -106.35},
    "INT": {"name": "Internacional", "lat": 20.0, "lng": -40.0},
    "XX": {"name": "Sin ubicar", "lat": 8.0, "lng": -30.0},
}

_ALIASES: list[tuple[str, str]] = [
    ("estados unidos", "US"),
    ("united states", "US"),
    ("ee. uu", "US"),
    ("eeuu", "US"),
    ("u.s.a", "US"),
    ("usa", "US"),
    ("méxico", "MX"),
    ("mexico", "MX"),
    ("guatemala", "GT"),
    ("honduras", "HN"),
    ("el salvador", "SV"),
    ("nicaragua", "NI"),
    ("costa rica", "CR"),
    ("panamá", "PA"),
    ("panama", "PA"),
    ("colombia", "CO"),
    ("venezuela", "VE"),
    ("brasil", "BR"),
    ("brazil", "BR"),
    ("argentina", "AR"),
    ("chile", "CL"),
    ("perú", "PE"),
    ("peru", "PE"),
    ("ecuador", "EC"),
    ("bolivia", "BO"),
    ("uruguay", "UY"),
    ("paraguay", "PY"),
    ("cuba", "CU"),
    ("república dominicana", "DO"),
    ("australia", "AU"),
    ("china", "CN"),
    ("japón", "JP"),
    ("japan", "JP"),
    ("india", "IN"),
    ("españa", "ES"),
    ("spain", "ES"),
    ("francia", "FR"),
    ("france", "FR"),
    ("alemania", "DE"),
    ("germany", "DE"),
    ("reino unido", "GB"),
    ("united kingdom", "GB"),
    ("suiza", "CH"),
    ("woah", "CH"),
    ("ginebra", "CH"),
    ("canadá", "CA"),
    ("canada", "CA"),
    ("sudáfrica", "ZA"),
    ("south africa", "ZA"),
    ("nigeria", "NG"),
    ("egipto", "EG"),
    ("belice", "BZ"),
    ("belize", "BZ"),
]


def country_info(code: str | None) -> dict[str, Any]:
    key = (code or "XX").upper()
    meta = COUNTRY_META.get(key) or {"name": key, "lat": 15.0, "lng": -50.0}
    return {"country": key, "name": meta["name"], "lat": meta["lat"], "lng": meta["lng"]}


def parse_countries(text: str) -> list[str]:
    blob = (text or "").lower()
    found: list[str] = []
    seen: set[str] = set()
    for needle, iso in sorted(_ALIASES, key=lambda kv: -len(kv[0])):
        if needle and needle in blob and iso not in seen:
            seen.add(iso)
            found.append(iso)
    return found


def resolve_article_country(article: dict[str, Any], extra_text: str = "") -> str:
    raw = (article.get("country") or "").strip().upper()
    title = article.get("title") or ""
    parsed = parse_countries(f"{title}\n{extra_text}")
    if raw in COUNTRY_META and raw not in {"XX", ""}:
        return raw
    if parsed:
        return parsed[0]
    if raw:
        return raw
    return "XX"


def load_generador_geo() -> dict[str, dict[str, Any]]:
    """Si el Excel/salida trae geo, úsalo; si no, centroides internos."""
    extra: dict[str, dict[str, Any]] = {}
    candidates = [
        SALIDA_DIR / "geo_paises.json",
        SALIDA_DIR / "geo.json",
        DATOS_DIR / "geo_paises.json",
        DATOS_DIR / "countries.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = data if isinstance(data, list) else data.get("countries") or data.get("features") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("country") or row.get("iso") or row.get("id") or "").upper()
            if not code:
                continue
            extra[code] = {
                "name": row.get("name") or COUNTRY_META.get(code, {}).get("name") or code,
                "lat": float(row.get("lat") or row.get("latitude") or COUNTRY_META.get(code, {}).get("lat") or 0),
                "lng": float(row.get("lng") or row.get("lon") or row.get("longitude") or COUNTRY_META.get(code, {}).get("lng") or 0),
            }
    if extra:
        COUNTRY_META.update(extra)
    return extra


load_generador_geo()
