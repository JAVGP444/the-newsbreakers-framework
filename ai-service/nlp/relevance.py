"""Relevancia de salud animal — embudo nivel 2.

Keywords desde Generador: diseases.yaml + enfermedades_config.yaml.
Score 0–1; por debajo de 0.15 se descarta (no sube de nivel).
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
    "h5n1", "cochliomyia", "screwworm", "senasica", "woah", "wahis",
    "zoonosis", "outbreak", "brote", "myiasis", "hog cholera",
    "avian influenza", "classical swine fever", "hpai", "animal health",
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
    # de-dup preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    if not unique:
        unique = list(FALLBACK_KEYWORDS)
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


def should_skip(text: str, threshold: float = RELEVANCE_THRESHOLD) -> bool:
    return relevance_score(text) < threshold


def should_analyze(text: str) -> str:
    """discard | low | analyze | high — embudo, no veredicto de verdad."""
    score = relevance_score(text)
    if score < RELEVANCE_THRESHOLD:
        return "discard"
    if score < 0.5:
        return "low"
    if score < 0.8:
        return "analyze"
    return "high"


def classify_topic(text: str) -> dict[str, Any]:
    return {
        "relevance": relevance_score(text),
        "bucket": should_analyze(text),
        "diseases": matched_diseases(text),
        "skip": should_skip(text),
        "threshold": RELEVANCE_THRESHOLD,
        "model_name": "keyword_relevance",
        "model_version": "diseases_yaml_v1",
    }
