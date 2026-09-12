"""Risk Engine — combina señales; nunca solo Fake/Real.

Pesos: evidencia, confiabilidad de fuente, reuso de imagen (pHash),
severidad del claim, crecimiento de narrativa, anomalía visual.

Veredictos:
  RESPALDADO | INSUFICIENTE | POSIBLEMENTE ENGAÑOSO | CONTRADICHO | REVISIÓN HUMANA
"""
from __future__ import annotations

import re
from typing import Any

MODEL_NAME = "risk_engine"
MODEL_VERSION = "weighted_v3"

WEIGHTS = {
    "evidence_contradiction": 0.28,
    "source_reliability": 0.22,
    "image_reuse": 0.18,
    "claim_severity": 0.18,
    "narrative_growth": 0.08,
    "visual_anomaly": 0.06,
}

PART_LABELS = {
    "evidence_contradiction": "Discrepancia con evidencia",
    "source_reliability": "Fuente poco fiable",
    "image_reuse": "Imagen reusada",
    "claim_severity": "Gravedad del claim",
    "narrative_growth": "Narrativa en crecimiento",
    "visual_anomaly": "Anomalía visual",
}

REVIEW_VERDICTS = frozenset({"CONTRADICHO", "POSIBLEMENTE ENGAÑOSO", "REVISIÓN HUMANA"})

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

TYPE_AUTHORITY = {
    "OFFICIAL": "A",
    "OFFICIAL_NATIONAL": "A",
    "OFFICIAL_INTERNATIONAL": "A",
    "RESEARCH": "B",
    "GENOMIC": "B",
    "EPIDEMIOLOGICAL": "B",
    "AGRICULTURAL": "B",
    "FACT_CHECK": "B",
    "NEWS": "C",
    "GENERAL_MEDIA": "C",
    "AGGREGATOR": "C",
    "YOUTUBE": "D",
    "SOCIAL": "E",
    "FORUM": "E",
}
CATEGORY_AUTHORITY = {
    "official": "A",
    "surveillance": "B",
    "veterinary": "B",
    "research": "B",
    "epidemiological": "B",
    "fact_check": "B",
    "media": "C",
    "youtube": "D",
    "social": "E",
    "forum": "E",
}
OFFICIAL_DOMAINS = (
    "woah.org",
    "oie.int",
    "who.int",
    "paho.org",
    "fao.org",
    "cdc.gov",
    "gob.mx",
    "senasica.gob.mx",
    "usda.gov",
    "aphis.usda.gov",
    "canada.ca",
    "inspection.gc.ca",
)
CASE_COUNT_RE = re.compile(
    r"(?<!\d)(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?:casos?|muertes?|deaths?|animales?|animals?|cabezas?|outbreaks?|brotes?)",
    re.I,
)
HITL_APPLY = {
    "validado": {"verdict": "RESPALDADO", "risk_score": 22, "rule": "hitl_validado"},
    "descartado": {"verdict": "CONTRADICHO", "risk_score": 82, "rule": "hitl_descartado"},
}

VISUAL_ANOMALY = {
    "POTENTIALLY_MANIPULATED": 92,
    "MEME": 72,
    "SOCIAL_MEDIA": 48,
    "NEWS_SCREENSHOT": 22,
    "INFOGRAPHIC": 28,
    "PHOTOGRAPH": 8,
    "OFFICIAL_DOCUMENT": 4,
    "ANIMAL_HEALTH_CONTENT": 12,
}


def _clip(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        n = 0.0
    return max(0.0, min(100.0, n))


def infer_authority(source: dict[str, Any] | None) -> str:
    source = source or {}
    current = str(source.get("authority") or "").strip().upper()
    if current in AUTHORITY_RELIABILITY:
        return current
    domain = str(source.get("domain") or "").lower().lstrip(".")
    if any(domain == d or domain.endswith("." + d) for d in OFFICIAL_DOMAINS):
        return "A"
    stype = str(source.get("type") or "").upper()
    if stype in TYPE_AUTHORITY:
        return TYPE_AUTHORITY[stype]
    cat = str(source.get("category") or "").lower()
    if cat in CATEGORY_AUTHORITY:
        return CATEGORY_AUTHORITY[cat]
    return ""


def source_unreliability(source: dict[str, Any] | None, hitl_shift: float = 0) -> float:
    """0 = fuente muy fiable (sube poco el riesgo); 100 = poco fiable."""
    source = source or {}
    authority = infer_authority(source)
    if authority in AUTHORITY_RELIABILITY:
        base = float(AUTHORITY_RELIABILITY[authority])
    else:
        stype = str(source.get("type") or "")
        if stype.upper() in OFFICIAL_TYPES or source.get("category") == "official":
            base = 12.0
        elif "RESEARCH" in stype.upper() or source.get("category") == "research":
            base = 20.0
        elif source.get("access_method") == "api":
            base = 40.0
        else:
            base = 55.0
    return _clip(base + float(hitl_shift or 0))


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


def extract_case_count(text: str | None) -> float | None:
    blob = text or ""
    found: list[float] = []
    for match in CASE_COUNT_RE.finditer(blob):
        raw = match.group(1).replace(",", "").replace(".", "")
        try:
            n = float(raw)
        except ValueError:
            continue
        if 1 <= n <= 5_000_000:
            found.append(n)
    return max(found) if found else None


def numeric_discrepancy(
    claims: list[dict[str, Any]] | None,
    evidence_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    claim_ns = [extract_case_count(c.get("text") if isinstance(c, dict) else str(c)) for c in (claims or [])]
    claim_ns = [n for n in claim_ns if n is not None]
    evid_ns = [extract_case_count(e.get("snippet") if isinstance(e, dict) else str(e)) for e in (evidence_rows or [])]
    evid_ns = [n for n in evid_ns if n is not None]
    if not claim_ns or not evid_ns:
        return {"score": 0.0, "reason": "", "claim": None, "official": None}
    claim_n = max(claim_ns)
    official_n = max(evid_ns)
    gap = abs(claim_n - official_n)
    ratio = max(claim_n, official_n) / max(min(claim_n, official_n), 1.0)
    if ratio >= 5 and gap >= 20:
        return {"score": 86.0, "reason": "cifra_parte", "claim": claim_n, "official": official_n}
    if ratio >= 2 and gap >= 10:
        return {"score": 62.0, "reason": "cifra_difiere", "claim": claim_n, "official": official_n}
    return {"score": 0.0, "reason": "", "claim": claim_n, "official": official_n}


def apply_hitl_label(label: str, reason: str = "") -> dict[str, Any] | None:
    spec = HITL_APPLY.get(str(label or "").strip().lower())
    if not spec:
        return None
    return {**spec, "reason": reason or ""}


def visual_anomaly_score(cnn_class: str | None, confidence: Any = None) -> float:
    base = float(VISUAL_ANOMALY.get(str(cnn_class or "").upper(), 0.0))
    if confidence is None:
        return _clip(base)
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 1.0
    if conf > 1.0:
        conf = conf / 100.0
    return _clip(base * max(0.45, min(1.0, conf)))


def image_reuse_score(reused: bool) -> float:
    return 78.0 if reused else 0.0


def narrative_growth_score(growth_pct: Any = None) -> float:
    try:
        growth = float(growth_pct or 0)
    except (TypeError, ValueError):
        growth = 0.0
    if growth <= 0:
        return 0.0
    return _clip(18.0 + growth * 0.65)


def _is_official_row(row: dict[str, Any] | None) -> bool:
    row = row or {}
    stype = str(row.get("source_type") or row.get("type") or "").upper()
    cat = str(row.get("category") or "")
    return stype in {t.upper() for t in OFFICIAL_TYPES} or cat == "official" or source_unreliability(row) <= 20


def cross_cut_score(
    peers: list[dict[str, Any]] | None,
    *,
    nli: str,
    severity: float,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cruce entre notas del mismo brote. No es Fake/Real: es si las fuentes parten."""
    peers = peers or []
    official_ok = [
        p
        for p in peers
        if _is_official_row(p) and str(p.get("verdict") or "") == "RESPALDADO"
    ]
    backed = [p for p in peers if str(p.get("verdict") or "") == "RESPALDADO"]
    contradicted = [p for p in peers if str(p.get("verdict") or "") == "CONTRADICHO"]
    this_official = _is_official_row(source)

    if official_ok and not this_official and (nli == "Contradicted" or severity >= 80):
        return {"score": 88.0, "reason": "discrepa_oficial", "peers": len(official_ok)}
    if official_ok and not this_official and nli == "Unknown":
        return {"score": 58.0, "reason": "no_cuadra_oficial", "peers": len(official_ok)}
    if backed and contradicted:
        return {"score": 72.0, "reason": "fuentes_parten", "peers": len(backed) + len(contradicted)}
    return {"score": 0.0, "reason": "", "peers": 0}


def collect_signals(
    *,
    nli_label: str | None,
    source: dict[str, Any] | None = None,
    claims: list[dict[str, Any]] | None = None,
    images: list[dict[str, Any]] | None = None,
    peers: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    growth_pct: Any = None,
    relevance: Any = 0,
    alert_threshold: int = 55,
    hitl_shift: float = 0,
) -> dict[str, Any]:
    nli = nli_label or "Unknown"
    severity = claim_severity_score(claims)
    evidence_score = 90.0 if nli == "Contradicted" else (10.0 if nli == "Supported" else 40.0)
    cut = cross_cut_score(peers, nli=nli, severity=severity, source=source)
    numbers = numeric_discrepancy(claims, evidence)
    evidence_score = max(evidence_score, float(cut["score"]), float(numbers["score"]))
    images = images or []
    reused = any(bool(im.get("reused")) for im in images)
    visual = 0.0
    for im in images:
        visual = max(visual, visual_anomaly_score(im.get("cnn_class"), im.get("cnn_confidence")))
    try:
        rel = float(relevance or 0)
    except (TypeError, ValueError):
        rel = 0.0
    return {
        "nli_label": nli,
        "evidence_contradiction": evidence_score,
        "source_reliability": source_unreliability(source, hitl_shift),
        "image_reuse": image_reuse_score(reused),
        "claim_severity": severity,
        "narrative_growth": narrative_growth_score(growth_pct),
        "visual_anomaly": visual,
        "alert_threshold": int(alert_threshold),
        "low_confidence": nli == "Unknown" and rel >= 0.8,
        "force_human_review": float(cut["score"]) >= 70 or float(numbers["score"]) >= 70,
        "cross_cut": cut,
        "numeric": numbers,
        "_source": source or {},
        "_claims": claims or [],
        "_images": images or [],
        "_relevance": rel,
        "_growth_pct": growth_pct,
    }


def needs_alert(risk: dict[str, Any], threshold: int = 55) -> bool:
    return int(risk.get("risk_score") or 0) >= int(threshold) or str(risk.get("verdict") or "") in REVIEW_VERDICTS


def _part_why(key: str, value: float, signals: dict[str, Any]) -> str:
    nli = str(signals.get("nli_label") or "Unknown")
    source = signals.get("_source") if isinstance(signals.get("_source"), dict) else {}
    claims = signals.get("_claims") if isinstance(signals.get("_claims"), list) else []
    images = signals.get("_images") if isinstance(signals.get("_images"), list) else []
    cut = signals.get("cross_cut") if isinstance(signals.get("cross_cut"), dict) else {}
    numbers = signals.get("numeric") if isinstance(signals.get("numeric"), dict) else {}
    if key == "evidence_contradiction":
        bits = [f"NLI de la afirmación: {nli}."]
        if nli == "Contradicted":
            bits.append("Choca con ficha oficial → 90.")
        elif nli == "Supported":
            bits.append("Cuadra con ficha oficial → 10.")
        else:
            bits.append("Sin overlap suficiente con ficha oficial → 40 de base.")
        if float(cut.get("score") or 0) > 0:
            bits.append(
                f"Cruce con {int(cut.get('peers') or 0)} notas del mismo brote ({cut.get('reason') or 'discrepancia'}) → {int(cut['score'])}."
            )
        if numbers.get("reason") and numbers.get("claim") is not None:
            bits.append(
                f"Cifra en la nota {numbers.get('claim')} vs parte oficial {numbers.get('official')} ({numbers.get('reason')}) → {int(numbers.get('score') or 0)}."
            )
        bits.append(f"Este parámetro toma el máximo de esas vías: {int(round(value))}.")
        return " ".join(bits)
    if key == "source_reliability":
        name = source.get("name") or source.get("domain") or source.get("source_id") or "fuente sin ficha"
        auth = infer_authority(source) or "sin letra"
        mapped = AUTHORITY_RELIABILITY.get(auth)
        bits = [f"Fuente: {name}."]
        bits.append(f"Autoridad {auth} (A=10 WOAH/SENASICA, C=45 prensa/agregador, E=75 redes).")
        if mapped is not None:
            bits.append(f"Tabla de autoridad → {int(mapped)}.")
        bits.append(f"Valor usado: {int(round(value))}.")
        return " ".join(bits)
    if key == "image_reuse":
        reused = any(bool(im.get("reused")) for im in images)
        if reused:
            return f"Hay pHash coincidente con otra nota del observatorio → {int(round(value))}."
        return "No hay reuso de imagen (pHash) → 0."
    if key == "claim_severity":
        if not claims:
            return "No hay afirmación estructurada → 0."
        types = sorted({str(c.get("pattern_type") or "titulo") for c in claims})
        preds = sorted({str(c.get("predicate") or "") for c in claims if c.get("predicate")})
        return (
            f"Patrón de afirmación: {', '.join(types)}"
            + (f"; predicado {', '.join(preds)}" if preds else "")
            + f" → {int(round(value))} (conspiración/oculta=80, brote o cifra=45, no verificable=35, resto=15)."
        )
    if key == "narrative_growth":
        growth = signals.get("_growth_pct")
        if not growth:
            return "Sin pico de narrativa medido en el periodo → 0."
        return f"Crecimiento de narrativa {growth}% → {int(round(value))} (18 + 0.65×crecimiento)."
    if key == "visual_anomaly":
        best = None
        best_v = -1.0
        for im in images:
            v = visual_anomaly_score(im.get("cnn_class"), im.get("cnn_confidence"))
            if v > best_v:
                best_v = v
                best = im
        if not best or best_v <= 0:
            return "Sin imagen clasificada → 0."
        klass = best.get("cnn_class") or "SIN_CLASE"
        conf = best.get("cnn_confidence")
        conf_txt = f", confianza visual {round(float(conf) * 100)}%" if conf is not None else ""
        return (
            f"Imagen {klass}{conf_txt}. Tabla: manipulación=92, meme=72, red social=48, "
            f"captura=22, foto=8. Valor: {int(round(value))}."
        )
    return f"Valor {int(round(value))}."


def explain_risk(
    parts: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signals = signals or {}
    parts = {k: _clip((parts or {}).get(k, signals.get(k, 0))) for k in WEIGHTS}
    rows = []
    total = 0.0
    terms = []
    for key, weight in WEIGHTS.items():
        value = parts[key]
        contrib = value * weight
        total += contrib
        terms.append(f"{int(round(value))}×{weight}")
        rows.append(
            {
                "id": key,
                "label": PART_LABELS[key],
                "value": round(value, 1),
                "weight": weight,
                "contrib": round(contrib, 2),
                "why": _part_why(key, value, signals),
            }
        )
    score = int(round(total))
    return {
        "score": score,
        "formula": " + ".join(terms) + f" = {score}",
        "rows": rows,
    }


def decorate_risk_why(
    why: dict[str, Any] | None,
    *,
    source: dict[str, Any] | None = None,
    claims: list[dict[str, Any]] | None = None,
    images: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    article: dict[str, Any] | None = None,
    peers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    why = dict(why or {})
    parts = why.get("parts") if isinstance(why.get("parts"), dict) else {}
    article = article or {}
    if not parts:
        nli = why.get("nli")
        if not nli and claims:
            labels = [str(c.get("nli_label") or "") for c in claims]
            nli = "Contradicted" if "Contradicted" in labels else ("Supported" if "Supported" in labels else "Unknown")
        signals = collect_signals(
            nli_label=nli or "Unknown",
            source=source,
            claims=claims,
            images=images,
            peers=peers,
            evidence=evidence,
            growth_pct=None,
            relevance=article.get("relevance_score"),
        )
        scored = risk_score(signals)
        why = {**scored["why"], **why}
        parts = scored["parts"]
        why["parts"] = parts
        why["parts_named"] = scored["why"].get("parts_named")
        why["explain"] = scored["why"].get("explain")
        return why
    signals = {
        "nli_label": why.get("nli") or "Unknown",
        "cross_cut": why.get("cross_cut") or {},
        "numeric": why.get("numeric") or {},
        "_source": source or {},
        "_claims": claims or [],
        "_images": images or [],
        "_relevance": article.get("relevance_score"),
        **parts,
    }
    why["explain"] = explain_risk(parts, signals=signals)
    why["parts_named"] = why.get("parts_named") or [
        {"id": k, "label": PART_LABELS[k], "value": parts.get(k, 0)} for k in WEIGHTS
    ]
    return why


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
    cut = signals.get("cross_cut") if isinstance(signals.get("cross_cut"), dict) else {}
    cut_score = _clip(cut.get("score") if cut else 0)
    numbers = signals.get("numeric") if isinstance(signals.get("numeric"), dict) else {}
    num_score = _clip(numbers.get("score") if numbers else 0)

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

    if verdict == "REVISIÓN HUMANA":
        if num_score >= 70:
            rule = "cifra_parte"
        elif cut_score >= 70:
            rule = "discrepancia"
        elif low_conf:
            rule = "baja_confianza"
        else:
            rule = "human"
    elif nli == "Contradicted":
        rule = "nli_contradicted"
    elif score >= 75:
        rule = "score_high"
    elif verdict == "RESPALDADO":
        rule = "supported_low_risk"
    elif verdict == "POSIBLEMENTE ENGAÑOSO":
        rule = "score_mid"
    else:
        rule = "insufficient_evidence"

    why = {
        "nli": nli or "Unknown",
        "score": score,
        "parts": parts,
        "parts_named": [{"id": k, "label": PART_LABELS[k], "value": parts[k]} for k in WEIGHTS],
        "threshold_alert": int(signals.get("alert_threshold") or 55),
        "rule": rule,
        "cross_cut": cut or {"score": 0, "reason": "", "peers": 0},
        "numeric": numbers or {"score": 0, "reason": "", "claim": None, "official": None},
        "explain": explain_risk(parts, signals=signals),
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
