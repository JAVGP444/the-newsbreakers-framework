"""Motor de narrativas — clustering de claims (MVP keyword; HDBSCAN Fase 15)."""
from __future__ import annotations

from engine import MODEL_NAME, MODEL_VERSION, cluster_claims

EXAMPLE_NARRATIVES = (
    "la enfermedad fue creada artificialmente",
    "las autoridades ocultan brotes",
    "las vacunas causan la enfermedad",
)

__all__ = ["cluster_claims", "MODEL_NAME", "MODEL_VERSION", "EXAMPLE_NARRATIVES"]
