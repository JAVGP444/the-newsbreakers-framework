"""Relevancia de salud animal — embudo nivel 2.

Keywords desde Generador (si existe) o `config/diseases.yaml` bundled.
Score 0–1; por debajo de 0.15 se descarta en medios generales.
Fuentes de la watchlist (oficial / veterinaria / investigación) se conservan
si hay una señal débil de sanidad animal — no hace falta TNB_DEMO_ROOT.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import DISEASES_YAML, ENFERMEDADES_CONFIG, ensure_paths  # noqa: E402

ensure_paths()

RELEVANCE_THRESHOLD = 0.15

FALLBACK_KEYWORDS = (
    "gusano barrenador", "gripe aviar", "peste porcina", "influenza aviar",
    "h5n1", "h5n2", "h5n6", "h7n9", "cochliomyia", "screwworm", "senasica",
    "woah", "wahis", "oie", "zoonosis", "outbreak", "brote", "myiasis",
    "hog cholera", "avian influenza", "classical swine fever", "hpai",
    "lpai", "animal health", "salud animal", "poultry", "livestock",
    "veterinary", "aves de corral", "bioseguridad", "epizoot",
    "new world screwworm", "bird flu", "swine fever", "foot and mouth",
    "aftosa", "rabia", "brucelosis", "tuberculosis bovina",
)

# Tipos/categorías de la watchlist que ya son sanidad animal.
WATCHLIST_KEEP_TYPES = {
    "official",
    "official_international",
    "veterinary_media",
    "veterinary",
    "research",
    "epidemiological",
    "genomic",
    "surveillance",
    "aggregator",
}
WATCHLIST_KEEP_CATEGORIES = {
    "official",
    "veterinary",
    "surveillance",
    "research",
    "epidemiological",
}

WEAK_ANIMAL_HEALTH = (
    "animal", "livestock", "poultry", "veterinary", "zoonos", "outbreak",
    "brote", "ganado", "aves", "farm", "influenza", "disease", "salud animal",
    "woah", "oie", "senasica", "fao", "wahis", "epizoot", "herd", "flock",
    "swine", "avian", "cattle", "pig", "bird flu", "vaccine", "vacuna",
    "cuarentena", "sanidad", "zoosanit", "h5n", "hpai", "screwworm",
    "barrenador", "porcino", "bovino", "ovino", "caprino", "equino",
    "pollo", "gallina", "pavo", "cerdo", "bioseguridad", "depopul",
    "sacrificio", "miasis", "myiasis", "pest", "peste", "corral",
    "aphis", "usda", "cidrap", "wahid",
)


def _add_kw(words: list[str], disease_map: dict[str, str], kw: str, did: str | None = None) -> None:
    kw = str(kw).lower().strip()
    if not kw:
        return
    words.append(kw)
    if did:
        disease_map[kw] = did


def _load_keywords() -> tuple[list[str], dict[str, str]]:
    words: list[str] = []
    disease_map: dict[str, str] = {}
    if DISEASES_YAML.exists():
        try:
            data = yaml.safe_load(DISEASES_YAML.read_text(encoding="utf-8")) or {}
            for did, info in (data.get("diseases") or {}).items():
                if not isinstance(info, dict):
                    continue
                for variant in info.get("variants") or []:
                    _add_kw(words, disease_map, variant, str(did))
                for species in info.get("species_affected") or []:
                    _add_kw(words, disease_map, species)
            for variant in (data.get("senasica") or {}).get("variants") or []:
                _add_kw(words, disease_map, variant)
            for bucket in (data.get("symptoms") or {}).values():
                if isinstance(bucket, list):
                    for kw in bucket:
                        _add_kw(words, disease_map, kw)
        except Exception:
            pass
    if ENFERMEDADES_CONFIG.exists():
        try:
            cfg = yaml.safe_load(ENFERMEDADES_CONFIG.read_text(encoding="utf-8")) or {}
            for did, info in (cfg.get("diseases") or {}).items():
                if not isinstance(info, dict):
                    continue
                for kw in info.get("keywords") or []:
                    _add_kw(words, disease_map, kw, str(did))
        except Exception:
            pass
    seen: set[str] = set()
    unique: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    if not unique:
        unique = list(FALLBACK_KEYWORDS)
    else:
        for extra in FALLBACK_KEYWORDS:
            if extra not in seen:
                unique.append(extra)
                seen.add(extra)
    return unique, disease_map


TOPIC_KEYWORDS, DISEASE_MAP = _load_keywords()


def relevance_score(text: str) -> float:
    t = (text or "").lower()
    if not t.strip():
        return 0.0
    hits = sum(1 for k in TOPIC_KEYWORDS if k in t)
    return min(1.0, hits / 3.0)


def matched_diseases(text: str) -> list[str]:
    t = (text or "").lower()
    found: set[str] = set()
    for kw, did in DISEASE_MAP.items():
        if kw in t:
            found.add(did)
    return sorted(found)


def _is_watchlist_animal_health(source: dict[str, Any] | None) -> bool:
    if not source:
        return False
    typ = str(source.get("type") or "").lower().replace(" ", "_")
    cat = str(source.get("category") or "").lower()
    if typ in WATCHLIST_KEEP_TYPES or cat in WATCHLIST_KEEP_CATEGORIES:
        return True
    if source.get("diseases"):
        return True
    domain = str(source.get("domain") or "").lower()
    if any(d in domain for d in ("woah.org", "fao.org", "who.int", "aphis.", "senasica", "cidrap", "poultry", "pigsite")):
        return True
    return False


def _has_weak_animal_health(text: str) -> bool:
    t = (text or "").lower()
    return any(tok in t for tok in WEAK_ANIMAL_HEALTH)


def should_skip(
    text: str,
    threshold: float = RELEVANCE_THRESHOLD,
    source: dict[str, Any] | None = None,
) -> bool:
    score = relevance_score(text)
    if score >= threshold:
        return False
    if _is_watchlist_animal_health(source):
        if score > 0 or _has_weak_animal_health(text) or source.get("diseases"):
            # Medios oficiales/vet de la watchlist: conservar RSS de sanidad animal
            # aunque el summary sea corto o falten tags del Generador.
            if score > 0 or _has_weak_animal_health(text):
                return False
            # Fuente con enfermedades asignadas + texto vacío/corto: no tirar el ítem
            if len((text or "").strip()) < 80:
                return False
    return True


def should_analyze(text: str, source: dict[str, Any] | None = None) -> str:
    """discard | low | analyze | high — embudo, no veredicto de verdad."""
    if should_skip(text, source=source):
        return "discard"
    score = relevance_score(text)
    if score < 0.5:
        return "low"
    if score < 0.8:
        return "analyze"
    return "high"


def classify_topic(text: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    skip = should_skip(text, source=source)
    return {
        "relevance": relevance_score(text),
        "bucket": should_analyze(text, source=source),
        "diseases": matched_diseases(text),
        "skip": skip,
        "watchlist_keep": bool(_is_watchlist_animal_health(source) and not skip),
        "threshold": RELEVANCE_THRESHOLD,
        "model_name": "keyword_relevance",
        "model_version": "diseases_yaml_v2_watchlist",
    }
