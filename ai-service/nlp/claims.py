"""Claims estructurados — sin etiqueta true/false.

Contrato: subject / predicate / object / location / animal / verifiable.
Reutiliza newsbreakers.analysis.claim_engine si TNB_DEMO_ROOT lo permite.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import PROJECT_ROOT, ensure_paths  # noqa: E402

ensure_paths()

from entities import ANIMALS, COUNTRIES, ORGS  # noqa: E402
from relevance import matched_diseases, relevance_score  # noqa: E402

CLAIM_PATTERNS = [
    (re.compile(r"[^.!?]*(?:casos?\s+(?:confirmados?|activos?|reportados?))[^.!?]*[.!?]", re.I), "casos"),
    (re.compile(r"[^.!?]*(?:brote|foco|rebrote|outbreak)[^.!?]*[.!?]", re.I), "brote"),
    (re.compile(r"[^.!?]*(?:SENASICA|cuarentena|sacrificio\s+sanitario|WOAH|OMSA)[^.!?]*[.!?]", re.I), "medida_oficial"),
    (re.compile(r"[^.!?]*(?:\d+\s*(?:%|por\s+ciento|casos?|muertes?|animales?))[^.!?]*[.!?]", re.I), "cifra"),
    (re.compile(r"[^.!?]*(?:propagación|expansión|frontera|riesgo|spread)[^.!?]*[.!?]", re.I), "propagacion"),
    (re.compile(r"[^.!?]*(?:vacuna|vacunación|erradicación|vaccine)[^.!?]*[.!?]", re.I), "control"),
    (re.compile(r"[^.!?]*(?:ocult\w+|laboratorio|arma\s+biol|cread[oa]\s+artificial)[^.!?]*[.!?]", re.I), "conspiracion"),
]

PREDICATES = [
    (re.compile(r"\bocult", re.I), "OCULTA"),
    (re.compile(r"\b(confirm|report|detect|anuncia|declara)", re.I), "REPORTA"),
    (re.compile(r"\b(causa|provoca|produce)", re.I), "CAUSA"),
    (re.compile(r"\b(niega|desmiente)", re.I), "NIEGA"),
    (re.compile(r"\b(vacun)", re.I), "VACUNA"),
    (re.compile(r"\b(brote|outbreak)", re.I), "BROTE_EN"),
]

MODEL_NAME = "claim_engine_structured"
MODEL_VERSION = "structured_v1"


def _first_match(text: str, vocab: dict[str, str]) -> str:
    lower = text.lower()
    for needle, canonical in sorted(vocab.items(), key=lambda kv: -len(kv[0])):
        if needle in lower:
            return canonical
    return ""


def _predicate(text: str) -> str:
    for pattern, label in PREDICATES:
        if pattern.search(text):
            return label
    return "AFIRMA"


def _subject(text: str) -> str:
    org = _first_match(text, ORGS)
    if org:
        return org
    diseases = matched_diseases(text)
    if diseases:
        return diseases[0]
    return (text.split() or ["fuente"])[0][:40]


def _object(text: str, subject: str, predicate: str) -> str:
    cleaned = text
    for token in (subject, predicate):
        if token:
            cleaned = re.sub(re.escape(token), " ", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip()[:240]


def structure_claim(text: str, pattern_type: str = "", diseases: list[str] | None = None) -> dict[str, Any]:
    diseases = diseases or matched_diseases(text)
    subject = _subject(text)
    predicate = _predicate(text)
    location = _first_match(text, COUNTRIES)
    animal = _first_match(text, ANIMALS)
    verifiable = bool(
        diseases
        or re.search(r"\d", text)
        or subject in ORGS.values()
        or pattern_type in {"casos", "cifra", "medida_oficial", "brote"}
    )
    cid = hashlib.sha256(text[:200].encode("utf-8")).hexdigest()[:32]
    return {
        "claim_id": cid,
        "text": text.strip(),
        "claim_text": text.strip(),
        "subject": subject,
        "predicate": predicate,
        "object": _object(text, subject, predicate),
        "location": location,
        "animal": animal,
        "verifiable": verifiable,
        "pattern_type": pattern_type,
        "diseases": diseases,
        "status": "unverified",
    }


def _local_extract(text: str) -> list[dict[str, Any]]:
    diseases = matched_diseases(text)
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pattern, ptype in CLAIM_PATTERNS:
        for match in pattern.finditer(text or ""):
            claim_text = match.group(0).strip()
            if len(claim_text) < 20 or claim_text in seen:
                continue
            seen.add(claim_text)
            row = structure_claim(claim_text, ptype, diseases)
            if ptype == "medida_oficial":
                row["status"] = "supported"
            claims.append(row)
    return claims[:8]


def _legacy_pack(text: str, topic_matches: list[str]) -> dict[str, Any] | None:
    """the-newsbreakers/api/claim_extractor.py — NER + search queries reales."""
    try:
        from claim_extractor import extract_claims as legacy_extract

        return legacy_extract(text or "", topic_matches)
    except Exception:
        return None


def _search_queries(text: str, diseases: list[str], locations: list[str]) -> list[str]:
    core = (diseases[:3] or ["animal disease outbreak"])[0]
    loc = locations[0] if locations else ""
    qs = [
        f'"{core}" site:woah.org OR site:who.int OR site:cdc.gov OR site:fao.org',
        f'"{core}" {loc} official report'.strip(),
        f'"{core}" SENASICA OR WAHIS outbreak',
        f'"{core}" fact check',
    ]
    return [q for q in qs if q.strip()][:6]


def extract_claims(text: str, topic_matches: list[str] | None = None) -> dict[str, Any]:
    topic_matches = topic_matches or []
    backend = "local_patterns"
    claims: list[dict[str, Any]] = []
    legacy = _legacy_pack(text or "", topic_matches)

    try:
        from newsbreakers.analysis.claim_engine import ClaimEngine

        engine = ClaimEngine()
        raw = engine.extract_claims("adhoc", text or "")
        backend = "newsbreakers.claim_engine"
        for row in raw[:8]:
            structured = structure_claim(
                row.get("claim_text") or "",
                row.get("pattern_type") or "",
                row.get("entity_refs") or topic_matches,
            )
            structured["claim_id"] = row.get("claim_id") or structured["claim_id"]
            structured["status"] = row.get("status") or "unverified"
            claims.append(structured)
    except Exception:
        claims = _local_extract(text or "")

    if not claims and (text or "").strip():
        snippet = (text or "")[:240]
        if legacy and legacy.get("claim_sentences"):
            snippet = str(legacy["claim_sentences"][0])[:240]
        elif legacy and legacy.get("main_claim"):
            snippet = str(legacy["main_claim"])[:240]
        claims = [structure_claim(snippet, "", matched_diseases(text or "") or topic_matches)]

    if legacy:
        backend = f"{backend}+legacy_claim_extractor"
        for sentence in (legacy.get("claim_sentences") or [])[:3]:
            if any(sentence[:80] in (c.get("text") or "") for c in claims):
                continue
            claims.append(structure_claim(sentence, "legacy", legacy.get("diseases") or topic_matches))

    diseases = list(dict.fromkeys((legacy or {}).get("diseases") or matched_diseases(text or "") or topic_matches))
    locations = list((legacy or {}).get("locations") or [])
    if not locations:
        from entities import COUNTRIES as _C

        lower = (text or "").lower()
        locations = [iso for needle, iso in _C.items() if needle in lower][:3]
    queries = list((legacy or {}).get("search_queries") or []) or _search_queries(text or "", diseases, locations)
    main = claims[0]["text"] if claims else ((legacy or {}).get("main_claim") or (text or "")[:240])
    return {
        "backend": backend,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "project_root": str(PROJECT_ROOT),
        "main_claim": main,
        "claims": claims[:8],
        "search_queries": queries[:8],
        "key_terms": topic_matches or diseases,
        "diseases": diseases,
        "animal_types": (legacy or {}).get("animal_types") or [],
        "locations": locations,
        "makes_outbreak_claim": any(c.get("pattern_type") == "brote" for c in claims)
        or bool((legacy or {}).get("makes_outbreak_claim")),
        "makes_false_transmission_claim": any(c.get("pattern_type") == "conspiracion" for c in claims)
        or bool((legacy or {}).get("makes_false_transmission_claim")),
        "has_mechanism_explanation": bool((legacy or {}).get("has_mechanism_explanation")),
        "relevance": relevance_score(text or ""),
        "raw": {"statuses_are_not_true_false": True, "legacy": bool(legacy)},
    }
