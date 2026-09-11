"""Clasificación de contenido / tipo de narrativa (contrato Fase 8+).

No es un veredicto FAKE/REAL. Categorías alineadas a docs/BASES_PROYECTO.md.
"""
from __future__ import annotations

from typing import Any

try:
    from .relevance import classify_topic
except ImportError:
    from relevance import classify_topic

NARRATIVE_TYPES = (
    "outbreak_minimization",
    "alarmism",
    "false_cause",
    "institutional_conspiracy",
    "zoonotic_misinfo",
    "false_foodborne",
    "official_update",
    "scientific_report",
    "unclassified",
)


def classify(text: str) -> dict[str, Any]:
    base = classify_topic(text)
    return {
        **base,
        "narrative_type": "unclassified",
        "labels": NARRATIVE_TYPES,
        "note": "Clasificador ML pendiente. Hoy: keywords de newsbreakers/dictionaries/diseases.yaml.",
    }
