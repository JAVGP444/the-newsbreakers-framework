"""Detección de idioma — langdetect si está instalado; si no, heurística."""
from __future__ import annotations

from typing import Any

SUPPORTED = {"es", "en", "fr", "pt", "de", "it", "zh", "ar", "ru", "ja"}

_ES = ("ción", "ción", "ñ", "á", "é", "í", "ó", "ú", "que ", "los ", "las ", "una ", "del ")
_EN = (" the ", " and ", " of ", " outbreak ", " confirmed ", " poultry ")
_PT = ("ção", "não", "uma ", "dos ", "surto")
_FR = (" les ", " une ", " des ", " grippe ", " foyer ")


def detect_language(text: str) -> str:
    blob = (text or "").strip()
    if len(blob) < 12:
        return "und"
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        lang = detect(blob)
        return lang if lang in SUPPORTED else lang[:2]
    except Exception:
        pass
    lower = f" {blob.lower()} "
    scores = {
        "es": sum(1 for t in _ES if t in lower),
        "en": sum(1 for t in _EN if t in lower),
        "pt": sum(1 for t in _PT if t in lower),
        "fr": sum(1 for t in _FR if t in lower),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "und"


def language_payload(text: str) -> dict[str, Any]:
    lang = detect_language(text)
    return {
        "language": lang,
        "model_name": "langdetect" if _has_langdetect() else "heuristic_lang",
        "model_version": "v1",
    }


def _has_langdetect() -> bool:
    try:
        import langdetect  # noqa: F401

        return True
    except Exception:
        return False
