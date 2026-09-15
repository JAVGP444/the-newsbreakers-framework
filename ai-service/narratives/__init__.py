"""Motor de narrativas — señales de léxico y clustering. Una palabra no es un veredicto."""
from __future__ import annotations

from engine import MODEL_NAME, MODEL_VERSION, cluster_claims
from lexicon import narrative_specs
from signals import METHOD, PRINCIPLE, analyze_article, analyze_text, classify_narrative, corpus_pack
from surveillance import characterize, dossier

EXAMPLE_NARRATIVES = (
    "la enfermedad fue creada artificialmente",
    "las autoridades ocultan brotes",
    "las vacunas causan la enfermedad",
)

__all__ = [
    "cluster_claims",
    "analyze_text",
    "analyze_article",
    "classify_narrative",
    "corpus_pack",
    "characterize",
    "dossier",
    "narrative_specs",
    "METHOD",
    "PRINCIPLE",
    "MODEL_NAME",
    "MODEL_VERSION",
    "EXAMPLE_NARRATIVES",
]
