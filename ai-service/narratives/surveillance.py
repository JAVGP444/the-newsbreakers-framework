"""Caracterización de narrativas: agrupar, evolucionar, contrastar. Nunca sella malicia."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from lexicon import narrative_specs
from signals import (
    METHOD,
    PRINCIPLE,
    analyze_text,
    classify_narrative,
    contrast_card,
    corpus_pack,
    evidence_use_by_host,
    modality,
)

OFFICIAL_HINTS = (
    "woah.org",
    "wahis",
    "who.int",
    "paho.org",
    "fao.org",
    "cdc.gov",
    "efsa.europa",
    "gob.mx",
    "senasica",
    "usda.gov",
    "aphis",
    "oie.int",
)

LIFECYCLE = (
    "origen",
    "aparicion",
    "crecimiento",
    "transformacion",
    "propagacion",
    "pico",
    "descenso",
    "recurrencia",
)


def _parse_dt(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _day(value: str | None) -> str:
    dt = _parse_dt(value)
    if dt:
        return dt.date().isoformat()
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(raw)
        if parsed:
            return parsed.date().isoformat()
    except Exception:
        pass
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        return raw[:10]
    return ""


def _host(url: str | None) -> str:
    try:
        return (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _is_official(host: str, source: dict[str, Any] | None = None) -> bool:
    blob = " ".join(
        [
            host,
            str((source or {}).get("type") or ""),
            str((source or {}).get("name") or ""),
            str((source or {}).get("category") or ""),
        ]
    ).lower()
    return any(k in blob for k in OFFICIAL_HINTS) or "oficial" in blob


def contrast_level(evidence: list[dict[str, Any]], claims: list[dict[str, Any]], days: int) -> dict[str, Any]:
    n = len(evidence)
    official = sum(1 for e in evidence if _is_official(_host(e.get("url"))))
    nli = sum(1 for c in claims if (c.get("nli_label") or "").lower() not in {"", "unknown", None})
    if n == 0:
        level = 0
        label = "No se pudo contrastar"
    elif nli == 0 and official == 0:
        level = 1
        label = "Coincidencia textual"
    elif official >= 1 and n < 3:
        level = 2
        label = "Comparación con fuentes"
    elif official >= 1 and n >= 3:
        level = 3
        label = "Varias fuentes"
    elif official >= 2 and days >= 3:
        level = 4
        label = "Evidencia y contexto temporal"
    else:
        level = 3
        label = "Varias fuentes"
    if official >= 2 and days >= 5 and n >= 5:
        level = 5
        label = "Evidencia, contexto, evolución"
    return {"level": level, "label": label, "evidence": n, "official": official}


def lifecycle_of(series: list[dict[str, Any]]) -> dict[str, Any]:
    counts = [int(p.get("count") or 0) for p in series]
    if not counts:
        return {"stage": "origen", "label": "Sin volumen aún", "stages": list(LIFECYCLE)}
    peak_i = max(range(len(counts)), key=lambda i: counts[i])
    first = next((i for i, n in enumerate(counts) if n), 0)
    last = next((i for i, n in reversed(list(enumerate(counts))) if n), 0)
    growth = counts[-1] > counts[0] if counts else False
    after_peak = peak_i < last
    down = after_peak and counts[-1] < counts[peak_i]
    rebound = down and any(counts[i] > counts[i - 1] for i in range(peak_i + 2, len(counts)))
    if rebound:
        stage, label = "recurrencia", "Creció, bajó y volvió"
    elif down:
        stage, label = "descenso", "Pasó el pico y baja"
    elif peak_i == last and growth:
        stage, label = "crecimiento", "Sigue creciendo"
    elif peak_i == last and counts[peak_i] >= max(counts or [0]):
        stage, label = "pico", "En el momento de más actividad"
    elif last - first >= 3:
        stage, label = "propagacion", "Se sostiene en el tiempo"
    else:
        stage, label = "aparicion", "Acaba de aparecer"
    return {
        "stage": stage,
        "label": label,
        "peak_day": series[peak_i]["day"] if series else None,
        "first_day": series[first]["day"] if series else None,
        "stages": list(LIFECYCLE),
        "note": "No todas las narrativas recorren todas las etapas.",
    }


def _priority(growth: float, volume: int, countries: int, classification: dict[str, Any], hide: bool) -> dict[str, Any]:
    code = "baja"
    why = "Poca actividad o evidencia clara."
    if volume >= 8 and (growth >= 40 or hide):
        code, why = "media", "Actividad moderada o acusación abierta."
    if volume >= 15 and growth >= 80 and (hide or classification.get("human_priority")):
        code, why = "alta", "Narrativa creciente con afirmaciones relevantes. Prioridad de investigación, no malicia."
    if volume >= 25 and growth >= 150 and countries >= 2 and hide:
        code, why = "critica", "Alta propagación y acusación sanitaria grave. Cola humana urgente; no es sentencia de intención."
    labels = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}
    return {"code": code, "label": labels[code], "why": why, "not_malice": True}


def _semantic_stages(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = sorted(articles, key=lambda a: _day(a.get("published_at") or a.get("collected_at")))
    if not dated:
        return []
    n = max(1, min(5, len(dated)))
    size = max(1, len(dated) // n)
    out = []
    for i in range(n):
        chunk = dated[i * size : (i + 1) * size if i < n - 1 else len(dated)]
        if not chunk:
            continue
        pack = analyze_text(" ".join(f"{r.get('title') or ''} {r.get('text') or ''}" for r in chunk[:40]))
        top = [c["term"] for c in (pack.get("cloud") or [])[:6]]
        out.append(
            {
                "stage": i + 1,
                "from": _day(chunk[0].get("published_at") or chunk[0].get("collected_at")),
                "to": _day(chunk[-1].get("published_at") or chunk[-1].get("collected_at")),
                "publications": len(chunk),
                "concepts": top,
                "note": "Qué vocabulario del banco aparece en esta ventana. No es un sello.",
            }
        )
    return out


def _match_pack(pack: dict[str, Any], text: str, spec: dict[str, Any]) -> bool:
    cats = {h["category"] for s in pack.get("signals") or [] for h in s.get("hits") or []}
    need = set(spec.get("categories") or ())
    extra = spec.get("extra_terms") or ()
    folded = (text or "").lower()
    extra_hit = any(str(t).lower() in folded for t in extra) if extra else True
    if extra and not extra_hit:
        return False
    if need and need.issubset(cats):
        return True
    if need and (need & cats) and extra_hit:
        return True
    strong = any(
        h.get("category") in need and int(h.get("weight") or 0) >= 4
        for s in pack.get("signals") or []
        for h in s.get("hits") or []
    )
    if need and (need & cats) and strong:
        return True
    return bool(need and (need & cats) and (pack.get("structures") or []))


def characterize(
    articles: list[dict[str, Any]],
    *,
    claims: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
    sample_limit: int = 220,
) -> dict[str, Any]:
    claims = list(claims or [])
    evidence = list(evidence or [])
    sources = list(sources or [])
    claims_by_art: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in claims:
        claims_by_art[str(c.get("content_id") or "")].append(c)
    evid_by_claim = defaultdict(list)
    for e in evidence:
        evid_by_claim[str(e.get("claim_id") or "")].append(e)

    used_hosts = evidence_use_by_host(evidence)
    catalog = []
    for src in sources:
        host = str(src.get("domain") or "").lower().removeprefix("www.")
        used = int(src.get("evidence_uses") or used_hosts.get(host) or 0)
        catalog.append(
            {
                "source_id": src.get("source_id"),
                "name": src.get("name") or src.get("source_id"),
                "type": src.get("type"),
                "country": src.get("country"),
                "active": bool(src.get("active", True)),
                "available": True,
                "used": used > 0,
                "evidence_uses": used,
                "documents": int(src.get("article_count") or 0),
                "official": _is_official(host, src),
                "last_checked": src.get("last_checked"),
            }
        )

    analyzed: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for art in articles[:sample_limit]:
        blob = f"{art.get('title') or ''} {art.get('text') or ''}"
        analyzed.append((art, analyze_text(blob), blob))

    rows = []
    alerts = []
    for spec in narrative_specs():
        matched = [art for art, pack, blob in analyzed if _match_pack(pack, blob, spec)]
        if not matched:
            continue
        dates = [_day(a.get("published_at") or a.get("collected_at")) for a in matched]
        dates = [d for d in dates if d]
        series_map: Counter[str] = Counter(dates)
        series = [{"day": d, "count": n} for d, n in sorted(series_map.items())]
        if len(series) >= 4:
            mid = len(series) // 2
            prev = sum(p["count"] for p in series[:mid]) or 1
            now = sum(p["count"] for p in series[mid:])
            growth = round(100.0 * (now - prev) / prev, 1)
        else:
            growth = 100.0 if matched else 0.0
        countries = Counter((a.get("country") or "XX") for a in matched)
        prop = []
        by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for a in matched:
            by_country[str(a.get("country") or "XX")].append(a)
        for cc, group in sorted(by_country.items(), key=lambda kv: -len(kv[1])):
            gdates = sorted(_day(x.get("published_at") or x.get("collected_at")) for x in group)
            gdates = [d for d in gdates if d]
            srcs = {x.get("source_id") for x in group if x.get("source_id")}
            peak = Counter(_day(x.get("published_at") or x.get("collected_at")) for x in group).most_common(1)
            prop.append(
                {
                    "country": cc,
                    "first_seen": gdates[0] if gdates else None,
                    "publications": len(group),
                    "sources": len(srcs),
                    "peak": peak[0][0] if peak else None,
                    "note": "Primer país detectado no es origen causal.",
                }
            )
        art_claims = []
        art_evid = []
        for a in matched:
            for c in claims_by_art.get(str(a.get("content_id")), []):
                item = dict(c)
                item["modality"] = modality(c.get("text") or "")
                art_claims.append(item)
                art_evid.extend(evid_by_claim.get(str(c.get("claim_id")), []))
        pack = analyze_text(" ".join((a.get("title") or "") for a in matched[:80]))
        classification = classify_narrative(pack, art_claims)
        hide = any(
            s.get("modality") == "afirmacion"
            and any(h.get("category") == "ocultamiento" for h in s.get("hits") or [])
            for s in pack.get("signals") or []
        )
        days = len(series)
        depth = contrast_level(art_evid, art_claims, days)
        life = lifecycle_of(series)
        prio = _priority(growth, len(matched), len(countries), classification, hide)
        stages = _semantic_stages(matched)
        by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for a in matched:
            by_source[str(a.get("source_id") or a.get("source_name") or "desconocida")].append(a)
        source_prop = []
        for sid, group in sorted(by_source.items(), key=lambda kv: -len(kv[1]))[:12]:
            gdates = sorted(filter(None, (_day(x.get("published_at") or x.get("collected_at")) for x in group)))
            source_prop.append(
                {
                    "source_id": sid,
                    "name": (group[0].get("source_name") or sid),
                    "country": group[0].get("country"),
                    "publications": len(group),
                    "first_seen": gdates[0] if gdates else None,
                    "last_seen": gdates[-1] if gdates else None,
                }
            )
        contrast = contrast_card(matched[0] if matched else {}, art_claims, art_evid, pack) if matched else None
        row = {
            "narrative_id": spec["id"],
            "label": spec["label"],
            "description": spec["description"],
            "theme": spec["label"],
            "keywords": list(spec.get("categories") or ()) + list(spec.get("extra_terms") or ()),
            "volume": len(matched),
            "growth_pct": growth,
            "state": life["stage"],
            "state_label": life["label"],
            "lifecycle": life,
            "first_seen": min(dates) if dates else None,
            "last_seen": max(dates) if dates else None,
            "countries": [{"country": k, "count": n} for k, n in countries.most_common()],
            "country_n": len([k for k in countries if k != "XX"]),
            "sources_n": len(by_source),
            "claims_n": len(art_claims),
            "classification": classification,
            "priority": prio,
            "contrast_level": depth,
            "series": series,
            "semantic_stages": stages,
            "propagation": prop,
            "source_propagation": source_prop,
            "articles": [
                {
                    "content_id": a.get("content_id"),
                    "title": a.get("title"),
                    "published_at": a.get("published_at"),
                    "country": a.get("country"),
                    "source_id": a.get("source_id"),
                }
                for a in matched[:12]
            ],
            "claims": [
                {
                    "claim_id": c.get("claim_id"),
                    "content_id": c.get("content_id"),
                    "text": c.get("text"),
                    "subject": c.get("subject"),
                    "predicate": c.get("predicate"),
                    "object": c.get("object"),
                    "modality": c.get("modality"),
                    "nli_label": c.get("nli_label"),
                    "verdict": c.get("verdict"),
                }
                for c in art_claims[:40]
            ],
            "evidence": [
                {
                    "evidence_id": e.get("evidence_id"),
                    "claim_id": e.get("claim_id"),
                    "url": e.get("url"),
                    "source_tier": e.get("source_tier"),
                    "snippet": (e.get("snippet") or "")[:280],
                    "stance": e.get("stance"),
                    "host": _host(e.get("url")),
                    "official": _is_official(_host(e.get("url"))),
                }
                for e in art_evid[:40]
            ],
            "contrast": contrast,
            "principle": PRINCIPLE,
            "origin_note": "El primer país detectado no implica origen causal.",
        }
        rows.append(row)
        if prio["code"] in {"alta", "critica"} or classification.get("human_priority"):
            alerts.append(
                {
                    "narrative_id": spec["id"],
                    "label": spec["label"],
                    "growth_pct": growth,
                    "priority": prio,
                    "reason": classification.get("why") or prio["why"],
                    "kind": "crecimiento" if growth >= 80 else "revision",
                }
            )

    rows.sort(key=lambda r: (0 - int(r["volume"]), 0 - float(r.get("growth_pct") or 0)))
    graph_pack = corpus_pack(articles[:sample_limit], force_min=1)
    return {
        "principle": PRINCIPLE,
        "method": METHOD,
        "narratives": rows,
        "alerts": alerts,
        "sources": catalog,
        "sources_available": len(catalog),
        "sources_used": sum(1 for s in catalog if s.get("used")),
        "graph": graph_pack.get("graph"),
        "cloud": graph_pack.get("cloud"),
        "pairs": graph_pack.get("pairs"),
        "structures": graph_pack.get("structures"),
        "categories": graph_pack.get("categories"),
        "sample": graph_pack.get("sample"),
        "bank": graph_pack.get("bank"),
        "kpis": {
            "narratives": len(rows),
            "active": sum(1 for r in rows if r.get("state") in {"crecimiento", "pico", "aparicion", "propagacion"}),
            "growing": sum(1 for r in rows if (r.get("growth_pct") or 0) >= 40),
            "priority": sum(1 for r in rows if r.get("priority", {}).get("code") in {"alta", "critica"}),
            "claims": sum(int(r.get("claims_n") or 0) for r in rows),
            "countries": len({c["country"] for r in rows for c in r.get("countries") or [] if c.get("country") not in {"XX", None}}),
        },
    }


def dossier(pack: dict[str, Any], narrative_id: str) -> dict[str, Any] | None:
    for row in pack.get("narratives") or []:
        if row.get("narrative_id") == narrative_id:
            return {**pack, "narrative": row, "narratives": pack.get("narratives")}
    return None
