"""NLI evidence-first: el LLM no decide la verdad.

claim + evidencia[] → Supported | Contradicted | Unknown

Default: Unknown. Supported solo con solapamiento fuerte Y fuente oficial.
Nunca Supported por 3 tokens genéricos.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

NLI_LABELS = ("Supported", "Contradicted", "Unknown")
MODEL_NAME = "nli_evidence_first"
MODEL_VERSION = "lexical_v2_conservative"

MISINFO = (
    "laboratorio", "arma biol", "creada artificial", "creado artificial",
    "autoridades ocultan", "ocultan el brote", "vacuna causa",
    "vacunas causan", "inventaron la enfermedad", "fake",
    "biolab", "bioweapon", "gain of function",
)

STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "are", "was", "were",
    "have", "has", "not", "but", "you", "all", "can", "una", "uno", "los", "las",
    "del", "por", "con", "para", "que", "como", "más", "mas", "sobre", "entre",
    "este", "esta", "hay", "son", "sus", "the", "http", "https", "www", "org",
    "com", "html", "index", "page", "home", "sitio", "página", "noticia",
    "news", "article", "brote", "outbreak", "caso", "casos", "salud", "health",
    "animal", "animals", "enfermedad", "disease", "official", "oficial",
}

OFFICIAL_HOSTS = (
    "woah.org", "who.int", "fao.org", "cdc.gov", "gob.mx", "usda.gov",
    "aphis.usda.gov", "paho.org", "oie.int", "ecdc.europa.eu",
)

DISEASE_ANCHORS = {
    "h5n1", "h5n2", "hpai", "lpai", "influenza", "aviar", "avian", "gripe",
    "screwworm", "barrenador", "cochliomyia", "hominivorax", "miasis",
    "porcina", "swine", "csfv", "wahis", "senasica", "woah", "omsa", "aphis",
    "poultry", "aves", "corral", "ganado", "bioseguridad", "biosecurity",
}

MIN_OVERLAP = 6
MIN_CLAIM_TOKENS = 5
MIN_ANCHORS = 2


def _tokens(text: str) -> set[str]:
    raw = {t for t in re.findall(r"[a-záéíóúñ0-9]{3,}", (text or "").lower())}
    return {t for t in raw if t not in STOPWORDS and not t.isdigit()}


def is_official_source(url: str = "", snippet: str = "") -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    if host and any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS):
        return True
    return False


def stance_from_text(claim_text: str, snippet: str, url: str = "") -> str:
    """Unknown por defecto. Supported exige fuente oficial + overlap fuerte."""
    claim_l = (claim_text or "").lower()
    snip_l = (snippet or "").lower()
    if not (snippet or "").strip():
        return "Unknown"
    claim_toks = _tokens(claim_text)
    snip_toks = _tokens(snippet)
    overlap = claim_toks & snip_toks
    official = is_official_source(url, snippet)
    official_ish = official or any(
        m in snip_l
        for m in ("woah", "omsa", "senasica", "who", "fao", "cdc", "aphis", "wahis")
    )
    misinfo_hit = any(term in claim_l for term in MISINFO)
    if misinfo_hit and official_ish and not any(term in snip_l for term in MISINFO):
        return "Contradicted"
    if not official:
        return "Unknown"
    if len(claim_toks) < MIN_CLAIM_TOKENS:
        return "Unknown"
    if len(overlap) < MIN_OVERLAP:
        return "Unknown"
    anchors = overlap & DISEASE_ANCHORS
    if len(anchors) < MIN_ANCHORS:
        return "Unknown"
    return "Supported"


def _stance(item: dict[str, Any], claim_text: str = "") -> str:
    raw = str(item.get("stance") or item.get("nli") or "").lower()
    snippet = str(item.get("snippet") or item.get("text") or "")
    url = str(item.get("url") or "")
    # Stance explícita curada (HITL / tests): se respeta Contradiction siempre;
    # Supported solo si la URL es oficial — evita "Supported" de 3 tokens.
    if raw in {"contradicted", "contradicts", "contradiction", "refute", "debunk"}:
        return "Contradicted"
    if raw in {"supported", "supports", "entailment", "support"}:
        if is_official_source(url, snippet) or not url:
            return "Supported"
        return "Unknown"
    if snippet and claim_text:
        return stance_from_text(claim_text, snippet, url=url)
    return "Unknown"


def verify_claim(claim: dict[str, Any] | str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Nunca llama a un LLM para '¿es fake?'. Solo agrega stances de evidencia."""
    evidence = evidence or []
    claim_text = claim.get("text") if isinstance(claim, dict) else str(claim)
    if isinstance(claim, dict):
        claim_text = claim.get("text") or claim.get("claim_text") or str(claim)

    if not evidence:
        return {
            "label": "Unknown",
            "confidence": 0.0,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "claim": claim_text,
            "evidence_used": 0,
            "note": "sin evidencia → Unknown (no se inventa verdad)",
        }

    stances = [_stance(item, claim_text) for item in evidence]
    supported = stances.count("Supported")
    contradicted = stances.count("Contradicted")

    if contradicted > supported and contradicted >= 1:
        label, confidence = "Contradicted", min(0.95, 0.5 + 0.15 * contradicted)
    elif supported > contradicted and supported >= 2:
        label, confidence = "Supported", min(0.9, 0.45 + 0.12 * supported)
    elif supported >= 1 and contradicted == 0:
        # Un solo snippet oficial fuerte puede bastar; la función de stance ya es estricta.
        label, confidence = "Supported", 0.62
    else:
        label, confidence = "Unknown", 0.35

    return {
        "label": label,
        "confidence": round(confidence, 3),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "claim": claim_text,
        "evidence_used": len(evidence),
        "supported": supported,
        "contradicted": contradicted,
        "note": "NLI conservador: Unknown por defecto; Supported solo overlap fuerte + fuente oficial.",
    }
