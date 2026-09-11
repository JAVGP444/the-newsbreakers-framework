"""NLP del framework — observatorio Generador_Excel_Enfermedades."""
from __future__ import annotations

try:
    from .claims import extract_claims
    from .entities import extract_entities
    from .language import detect_language
    from .relevance import matched_diseases, relevance_score, should_analyze, should_skip
except ImportError:
    from claims import extract_claims
    from entities import extract_entities
    from language import detect_language
    from relevance import matched_diseases, relevance_score, should_analyze, should_skip

__all__ = [
    "detect_language",
    "extract_claims",
    "extract_entities",
    "matched_diseases",
    "relevance_score",
    "should_analyze",
    "should_skip",
]
