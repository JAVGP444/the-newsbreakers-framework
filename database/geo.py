"""Países, lugares y centroides para el mapa del observatorio."""
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

# Más específico primero: condado antes que estado, Baja California antes que California.
PLACES: list[dict[str, Any]] = [
    {
        "id": "US-TX-PRESIDIO",
        "name": "Presidio, Texas",
        "country": "US",
        "lat": 29.561,
        "lng": -104.373,
        "needles": ("presidio county", "presidio, texas", "presidio"),
        "query": "Presidio",
    },
    {
        "id": "US-TX-JEFFDAVIS",
        "name": "Jeff Davis, Texas",
        "country": "US",
        "lat": 30.746,
        "lng": -104.140,
        "needles": ("jeff davis county", "jeff davis", "jeffdavis"),
        "query": "Jeff Davis",
    },
    {
        "id": "MX-BC",
        "name": "Baja California",
        "country": "MX",
        "lat": 30.84,
        "lng": -115.28,
        "needles": ("baja california sur", "baja california"),
        "query": "Baja California",
    },
    {
        "id": "US-NM",
        "name": "Nuevo México",
        "country": "US",
        "lat": 34.41,
        "lng": -106.11,
        "needles": ("new mexico", "nuevo méxico", "nuevo mexico"),
        "query": "New Mexico",
    },
    {
        "id": "US-TX",
        "name": "Texas",
        "country": "US",
        "lat": 31.0,
        "lng": -99.9,
        "needles": ("texas",),
        "query": "Texas",
    },
    {
        "id": "US-AZ",
        "name": "Arizona",
        "country": "US",
        "lat": 34.27,
        "lng": -111.66,
        "needles": ("arizona",),
        "query": "Arizona",
    },
    {
        "id": "US-CA",
        "name": "California",
        "country": "US",
        "lat": 36.78,
        "lng": -119.42,
        "needles": ("california",),
        "query": "California",
    },
    {
        "id": "US-FL",
        "name": "Florida",
        "country": "US",
        "lat": 27.66,
        "lng": -81.52,
        "needles": ("florida",),
        "query": "Florida",
    },
    {
        "id": "US-IA",
        "name": "Iowa",
        "country": "US",
        "lat": 42.0,
        "lng": -93.5,
        "needles": ("iowa",),
        "query": "Iowa",
    },
    {
        "id": "US-NC",
        "name": "Carolina del Norte",
        "country": "US",
        "lat": 35.76,
        "lng": -79.02,
        "needles": ("north carolina", "carolina del norte"),
        "query": "North Carolina",
    },
    {
        "id": "MX-CHIS",
        "name": "Chiapas",
        "country": "MX",
        "lat": 16.75,
        "lng": -93.13,
        "needles": ("chiapas",),
        "query": "Chiapas",
    },
    {
        "id": "MX-OAX",
        "name": "Oaxaca",
        "country": "MX",
        "lat": 17.07,
        "lng": -96.72,
        "needles": ("oaxaca",),
        "query": "Oaxaca",
    },
    {
        "id": "MX-TAB",
        "name": "Tabasco",
        "country": "MX",
        "lat": 17.84,
        "lng": -92.62,
        "needles": ("tabasco",),
        "query": "Tabasco",
    },
    {
        "id": "MX-VER",
        "name": "Veracruz",
        "country": "MX",
        "lat": 19.17,
        "lng": -96.13,
        "needles": ("veracruz",),
        "query": "Veracruz",
    },
    {
        "id": "MX-YUC",
        "name": "Yucatán",
        "country": "MX",
        "lat": 20.71,
        "lng": -89.09,
        "needles": ("yucatán", "yucatan"),
        "query": "Yucatán",
    },
    {
        "id": "MX-CAM",
        "name": "Campeche",
        "country": "MX",
        "lat": 19.83,
        "lng": -90.53,
        "needles": ("campeche",),
        "query": "Campeche",
    },
    {
        "id": "MX-ROO",
        "name": "Quintana Roo",
        "country": "MX",
        "lat": 19.18,
        "lng": -88.05,
        "needles": ("quintana roo",),
        "query": "Quintana Roo",
    },
    {
        "id": "MX-TAMPS",
        "name": "Tamaulipas",
        "country": "MX",
        "lat": 24.27,
        "lng": -98.84,
        "needles": ("tamaulipas",),
        "query": "Tamaulipas",
    },
    {
        "id": "MX-NL",
        "name": "Nuevo León",
        "country": "MX",
        "lat": 25.59,
        "lng": -99.99,
        "needles": ("nuevo león", "nuevo leon"),
        "query": "Nuevo León",
    },
    {
        "id": "MX-COAH",
        "name": "Coahuila",
        "country": "MX",
        "lat": 27.06,
        "lng": -101.71,
        "needles": ("coahuila",),
        "query": "Coahuila",
    },
    {
        "id": "MX-CHIH",
        "name": "Chihuahua",
        "country": "MX",
        "lat": 28.63,
        "lng": -106.07,
        "needles": ("chihuahua",),
        "query": "Chihuahua",
    },
    {
        "id": "MX-GTO",
        "name": "Guanajuato",
        "country": "MX",
        "lat": 21.02,
        "lng": -101.26,
        "needles": ("guanajuato",),
        "query": "Guanajuato",
    },
    {
        "id": "MX-JAL",
        "name": "Jalisco",
        "country": "MX",
        "lat": 20.66,
        "lng": -103.35,
        "needles": ("jalisco",),
        "query": "Jalisco",
    },
    {
        "id": "MX-SON",
        "name": "Sonora",
        "country": "MX",
        "lat": 29.30,
        "lng": -110.93,
        "needles": ("sonora",),
        "query": "Sonora",
    },
    {
        "id": "MX-SIN",
        "name": "Sinaloa",
        "country": "MX",
        "lat": 25.17,
        "lng": -107.48,
        "needles": ("sinaloa",),
        "query": "Sinaloa",
    },
    {
        "id": "MX-GRO",
        "name": "Guerrero",
        "country": "MX",
        "lat": 17.44,
        "lng": -99.55,
        "needles": ("guerrero",),
        "query": "Guerrero",
    },
    {
        "id": "MX-PUE",
        "name": "Puebla",
        "country": "MX",
        "lat": 19.04,
        "lng": -98.21,
        "needles": ("puebla",),
        "query": "Puebla",
    },
]

PLACE_BY_ID: dict[str, dict[str, Any]] = {p["id"]: p for p in PLACES}

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


_MASK_PHRASES: dict[str, tuple[str, ...]] = {
    "mexico": ("new mexico", "nuevo mexico", "nuevo méxico"),
    "méxico": ("nuevo méxico", "new mexico", "nuevo mexico"),
    "california": ("baja california sur", "baja california"),
}


def _text_hit(blob: str, needle: str) -> bool:
    """Evita que 'usa' dentro de 'gusano' cuente como Estados Unidos."""
    if not needle:
        return False
    masked = blob
    for phrase in _MASK_PHRASES.get(needle, ()):
        masked = masked.replace(phrase, " ")
    if " " in needle or "." in needle:
        return needle in masked
    return re.search(rf"(?<![a-záéíóúüñ]){re.escape(needle)}(?![a-záéíóúüñ])", masked) is not None


def country_info(code: str | None) -> dict[str, Any]:
    key = (code or "XX").upper()
    if key not in COUNTRY_META or key in {"XX", "INT"}:
        name = (COUNTRY_META.get(key) or {}).get("name") or "Sin ubicar"
        return {
            "country": key if key in COUNTRY_META else "XX",
            "name": name,
            "lat": None,
            "lng": None,
            "unlocated": True,
        }
    meta = COUNTRY_META[key]
    return {"country": key, "name": meta["name"], "lat": meta["lat"], "lng": meta["lng"]}


def place_info(place_id: str | None) -> dict[str, Any] | None:
    meta = PLACE_BY_ID.get((place_id or "").upper())
    if not meta:
        return None
    return {
        "place_id": meta["id"],
        "name": meta["name"],
        "country": meta["country"],
        "lat": meta["lat"],
        "lng": meta["lng"],
        "grain": "place",
        "query": meta["query"],
        "unlocated": False,
    }


def parse_countries(text: str) -> list[str]:
    blob = (text or "").lower()
    found: list[str] = []
    seen: set[str] = set()
    for needle, iso in sorted(_ALIASES, key=lambda kv: -len(kv[0])):
        if needle and _text_hit(blob, needle) and iso not in seen:
            seen.add(iso)
            found.append(iso)
    return found


def _blob_for(article: dict[str, Any], extra_text: str = "") -> str:
    raw = article.get("country") or ""
    title = article.get("title") or ""
    text = (article.get("text") or "")[:800]
    return f"{raw}\n{title}\n{extra_text}\n{text}".lower()


def _match_place(blob: str) -> dict[str, Any] | None:
    for place in PLACES:
        if any(_text_hit(blob, needle) for needle in place["needles"]):
            return place
    return None


def resolve_article_country(article: dict[str, Any], extra_text: str = "") -> str:
    raw = (article.get("country") or "").strip()
    raw_up = raw.upper()
    if raw_up in PLACE_BY_ID:
        return PLACE_BY_ID[raw_up]["country"]
    if raw_up in COUNTRY_META and raw_up not in {"XX", "INT", ""}:
        return raw_up
    blob = _blob_for(article, extra_text)
    place = _match_place(blob)
    if place:
        return place["country"]
    parsed = parse_countries(blob)
    if parsed:
        return parsed[0]
    return "XX"


def resolve_article_place(article: dict[str, Any], extra_text: str = "") -> dict[str, Any]:
    """Estado, condado o país. El punto del mapa debe ser el lugar que nombra la nota."""
    raw = (article.get("country") or "").strip().upper()
    if raw in PLACE_BY_ID:
        info = place_info(raw)
        if info:
            return info
    place = _match_place(_blob_for(article, extra_text))
    if place:
        info = place_info(place["id"])
        if info:
            return info
    code = resolve_article_country(article, extra_text)
    geo = country_info(code)
    unlocated = bool(geo.get("unlocated") or code in {"XX", "INT"})
    return {
        "place_id": code if code in COUNTRY_META else "XX",
        "name": geo["name"],
        "country": code if code in COUNTRY_META else "XX",
        "lat": None if unlocated else geo.get("lat"),
        "lng": None if unlocated else geo.get("lng"),
        "grain": "country",
        "query": None,
        "unlocated": unlocated,
    }


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
