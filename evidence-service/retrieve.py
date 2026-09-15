"""Evidence Engine — prioridad oficial > internacional > científica > periodística.

Recupera snippets reales de fichas oficiales (cache 24 h). No usa un LLM
para decidir la verdad ni homepages genéricas como prueba.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import PROJECT_ROOT, ensure_paths  # noqa: E402

ensure_paths()

from live_pages import live_event_cards, live_evidence_cards  # noqa: E402
from nli import stance_from_text  # noqa: E402
from safe_urls import public_http_url  # noqa: E402


def retrieve_evidence(claim: dict[str, Any] | str, limit: int = 5) -> list[dict[str, Any]]:
    text = claim.get("text") if isinstance(claim, dict) else str(claim)
    diseases: list[str] = []
    if isinstance(claim, dict):
        text = claim.get("text") or claim.get("claim_text") or ""
        diseases = [str(d) for d in (claim.get("diseases") or []) if d]
    if not diseases:
        try:
            from relevance import matched_diseases

            diseases = matched_diseases(text or "")
        except Exception:
            diseases = []
    live = live_event_cards(diseases, text or "", limit=limit)
    if not live:
        live = live_evidence_cards(diseases, limit=limit)
    if not live:
        try:
            from database.enrich import disease_evidence_cards

            live = []
            for card in disease_evidence_cards(diseases):
                url = public_http_url(str(card.get("url") or "")) or ""
                if not url:
                    continue
                live.append(
                    {
                        "url": url,
                        "title": card.get("title") or "",
                        "snippet": card.get("snippet") or "",
                        "tier": "official",
                    }
                )
        except Exception:
            live = []
    if live and not any(c.get("event") for c in live):
        try:
            from database.enrich import cap_official_cards

            live = cap_official_cards(live, diseases, limit=min(limit, 4))
        except Exception:
            pass
    out: list[dict[str, Any]] = []
    for item in live[:limit]:
        url = public_http_url(str(item.get("url") or "")) or ""
        if not url:
            continue
        snippet = str(item.get("snippet") or "")
        if len(snippet.strip()) < 40:
            continue
        stance = stance_from_text(text or "", snippet, url=url)
        eid = hashlib.sha256(f"{text}:{url}".encode("utf-8")).hexdigest()[:16]
        out.append(
            {
                "evidence_id": f"EV-{eid}",
                "url": url,
                "tier": item.get("tier") or "official",
                "source_tier": item.get("tier") or "official",
                "snippet": snippet[:900],
                "stance": stance,
                "claim": text,
                "note": f"Ficha oficial viva / cache 24 h ({PROJECT_ROOT.name})",
            }
        )
    return out


def retrieve_from_legacy(text: str) -> dict[str, Any] | None:
    try:
        from newsbreakers.analysis.claim_engine import ClaimEngine

        claims = ClaimEngine().extract_claims("adhoc", text)
        return {"backend": "newsbreakers.claim_engine", "claims": claims}
    except Exception:
        return None
