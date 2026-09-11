"""Risk Engine — combina señales; nunca solo Fake/Real.

Pesos: evidencia, confiabilidad de fuente, reuso de imagen (pHash),
severidad del claim. Cada predicción lleva model_version.

Veredictos:
  RESPALDADO | INSUFICIENTE | POSIBLEMENTE ENGAÑOSO | CONTRADICHO | REVISIÓN HUMANA
"""
from __future__ import annotations

from typing import Any

MODEL_NAME = "risk_engine"
MODEL_VERSION = "weighted_v1"

WEIGHTS = {
    "evidence_contradiction": 0.28,
    "source_reliability": 0.22,
    "image_reuse": 0.18,
    "claim_severity": 0.18,
    "narrative_growth": 0.08,
    "visual_anomaly": 0.06,
}

DISPLAY_VERDICTS = (
    "RESPALDADO",
    "INSUFICIENTE",
    "POSIBLEMENTE ENGAÑOSO",
    "CONTRADICHO",
    "REVISIÓN HUMANA",
)

AUTHORITY_RELIABILITY = {
    "A": 10,
    "B": 25,
    "C": 45,
    "D": 60,
    "E": 75,
    "F": 90,
}

OFFICIAL_TYPES = {"OFFICIAL", "OFFICIAL_NATIONAL", "OFFICIAL_INTERNATIONAL", "official"}


def _clip(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        n = 0.0
    return max(0.0, min(100.0, n))


def source_unreliability(source: dict[str, Any] | None) -> float:
    """0 = fuente muy fiable (sube poco el riesgo); 100 = poco fiable."""
    source = source or {}
    authority = str(source.get("authority") or "").upper()
    if authority in AUTHORITY_RELIABILITY:
        return float(AUTHORITY_RELIABILITY[authority])
    stype = str(source.get("type") or "")
    if stype.upper() in OFFICIAL_TYPES or source.get("category") == "official":
        return 12.0
    if "RESEARCH" in stype.upper() or source.get("category") == "research":
        return 20.0
    if source.get("access_method") == "api":
        return 40.0
    return 55.0


def claim_severity_score(claims: list[dict[str, Any]] | None) -> float:
    claims = claims or []
    score = 0.0
    for claim in claims:
        ptype = str(claim.get("pattern_type") or "")
        pred = str(claim.get("predicate") or "")
        if ptype == "conspiracion" or pred in {"OCULTA", "CAUSA"}:
            score = max(score, 80.0)
        elif ptype in {"brote", "cifra"}:
            score = max(score, 45.0)
        elif not claim.get("verifiable", True):
            score = max(score, 35.0)
        else:
            score = max(score, 15.0)
    return score


def risk_score(signals: dict[str, Any] | None = None) -> dict[str, Any]:
    signals = signals or {}
    parts: dict[str, float] = {}
    weighted = 0.0
    for key, weight in WEIGHTS.items():
        val = _clip(signals.get(key, 0))
        parts[key] = val
        weighted += val * weight
    score = int(round(weighted))

    nli = str(signals.get("nli_label") or "")
    low_conf = bool(signals.get("low_confidence"))
    human = bool(signals.get("force_human_review"))

    if human or low_conf:
        verdict = "REVISIÓN HUMANA"
    elif nli == "Contradicted" or score >= 75:
        verdict = "CONTRADICHO"
    elif nli == "Supported" and score < 35:
        verdict = "RESPALDADO"
    elif score >= 55:
        verdict = "POSIBLEMENTE ENGAÑOSO"
    elif nli == "Supported":
        verdict = "RESPALDADO"
    else:
        verdict = "INSUFICIENTE"

    why = {
        "nli": nli or "Unknown",
        "score": score,
        "parts": parts,
        "threshold_alert": int(signals.get("alert_threshold") or 55),
        "rule": (
            "human" if verdict == "REVISIÓN HUMANA"
            else "nli_contradicted" if nli == "Contradicted"
            else "score_high" if score >= 75
            else "supported_low_risk" if verdict == "RESPALDADO"
            else "score_mid" if verdict == "POSIBLEMENTE ENGAÑOSO"
            else "insufficient_evidence"
        ),
    }

    return {
        "risk_score": score,
        "verdict": verdict,
        "weights": WEIGHTS,
        "parts": parts,
        "why": why,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "nli_label": nli or None,
    }
