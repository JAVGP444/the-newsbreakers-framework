"""Narrativas MVP — clustering por keywords (vacunas, ocultamiento, artificial).

HDBSCAN queda para producción. Aquí hay una función real `cluster_claims`
que cuenta crecimiento vs el ciclo anterior en SQLite.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable

MODEL_NAME = "narrative_engine"
MODEL_VERSION = "keyword_cluster_v1"

CLUSTERS = (
    {
        "id": "NAR-vacunas",
        "label": "vacunas",
        "keywords": ("vacuna", "vacunación", "vaccine", "erradicación"),
    },
    {
        "id": "NAR-ocultamiento",
        "label": "ocultamiento",
        "keywords": ("oculta", "ocultamiento", "niega", "cover-up", "encubre", "encubrimiento"),
    },
    {
        "id": "NAR-artificial",
        "label": "artificial",
        "keywords": ("artificial", "laboratorio", "creada", "bioweapon", "arma biol"),
    },
    {
        "id": "NAR-brote",
        "label": "brote",
        "keywords": ("brote", "outbreak", "foco", "casos confirmados"),
    },
    {
        "id": "NAR-alarmismo",
        "label": "alarmismo",
        "keywords": ("pánico", "catástrofe", "letal", "inminente", "alarmista"),
    },
)


def _match(text: str) -> list[dict[str, str]]:
    lower = (text or "").lower()
    hits = []
    for cluster in CLUSTERS:
        if any(kw in lower for kw in cluster["keywords"]):
            hits.append(cluster)
    return hits


def cluster_claims(
    claims: Iterable[dict[str, Any]] | None = None,
    previous_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    claims = list(claims or [])
    previous_counts = previous_counts or {}
    buckets: dict[str, dict[str, Any]] = {
        c["id"]: {"narrative_id": c["id"], "label": c["label"], "keywords": list(c["keywords"]), "claim_ids": []}
        for c in CLUSTERS
    }
    for claim in claims:
        text = claim.get("text") or claim.get("claim_text") or ""
        cid = claim.get("claim_id") or hashlib.sha256(text.encode()).hexdigest()[:12]
        for cluster in _match(text):
            buckets[cluster["id"]]["claim_ids"].append(cid)

    rows = []
    growth: dict[str, float] = {}
    for nid, bucket in buckets.items():
        count = len(bucket["claim_ids"])
        prev = int(previous_counts.get(nid) or 0)
        if prev == 0:
            growth_pct = 100.0 if count else 0.0
        else:
            growth_pct = round(100.0 * (count - prev) / prev, 1)
        growth[bucket["label"]] = growth_pct
        rows.append(
            {
                **bucket,
                "claim_count": count,
                "prev_count": prev,
                "growth_pct": growth_pct,
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
            }
        )
    return {
        "clusters": rows,
        "growth": growth,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "implemented": True,
    }
