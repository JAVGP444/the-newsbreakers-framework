"""Verificación: NLI evidence-first. El LLM no es juez de verdad."""
from __future__ import annotations

try:
    from .llm import explain_with_evidence, probe_llm
    from .nli import NLI_LABELS, verify_claim
except ImportError:
    from llm import explain_with_evidence, probe_llm
    from nli import NLI_LABELS, verify_claim

__all__ = ["NLI_LABELS", "verify_claim", "explain_with_evidence", "probe_llm"]
