"""Contraste para revisión: hechos de la nota vs boletín oficial y otras notas."""
from __future__ import annotations

import os
import re
from typing import Any

from bootstrap import ensure_paths

ensure_paths()

from database.event_facts import (  # noqa: E402
    compare_facts,
    extract_facts,
    pick_paragraph,
    source_is_official,
)
from nli import DISEASE_ANCHORS, _tokens  # noqa: E402

GDELT_TAIL = re.compile(r"\s*20\d{6}T\d{6,9}Z\b.*$", re.S | re.I)
BIO_HINTS = (
    "joined the united nations",
    "secretary-general",
    "serving as un system",
    "coordinator of the m",
    "special representative for food",
)


def clean_claim_text(text: str | None) -> str:
    raw = GDELT_TAIL.sub("", text or "")
    return re.sub(r"\s+", " ", raw).strip()


def _looks_like_bio(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in BIO_HINTS)


def _claim_score(claim: dict[str, Any], title: str) -> int:
    text = clean_claim_text(claim.get("text") or "")
    if len(text) < 24:
        return -99
    if _looks_like_bio(text):
        return -99
    score = 0
    if claim.get("verifiable"):
        score += 2
    nli = str(claim.get("nli_label") or claim.get("verdict") or "")
    if nli in {"Supported", "Contradicted"}:
        score += 3
    shared = _tokens(text) & _tokens(title)
    score += min(4, len(shared))
    if DISEASE_ANCHORS & _tokens(text):
        score += 2
    if len(_tokens(text)) > 80:
        score -= 2
    return score


def pick_review_claim(claims: list[dict[str, Any]] | None, title: str = "") -> str:
    title_clean = clean_claim_text(title)
    ranked: list[tuple[int, dict[str, Any]]] = []
    for claim in claims or []:
        score = _claim_score(claim, title_clean)
        if score >= 0:
            ranked.append((score, claim))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if ranked:
        text = clean_claim_text(ranked[0][1].get("text") or "")
        if title_clean and len(_tokens(text) & _tokens(title_clean)) < 2 and len(_tokens(title_clean)) >= 4:
            return title_clean
        return text
    return title_clean


def _norm_title(text: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúñ]+", " ", (text or "").lower()).strip()


def _diseases_for(claim_text: str, item: dict[str, Any]) -> list[str]:
    try:
        from relevance import matched_diseases

        found = matched_diseases(claim_text) or matched_diseases(str(item.get("title") or ""))
        if found:
            return found
    except Exception:
        pass
    facts = extract_facts(claim_text)
    mapped = {
        "gusano barrenador": "gusano_barrenador",
        "gripe aviar": "gripe_aviar",
        "peste porcina": "fiebre_porcina_clasica",
    }
    return [mapped[d] for d in facts["diseases"] if d in mapped]


def _score_candidate(claim_text: str, snippet: str, official: bool) -> tuple[int, dict[str, Any]]:
    compared = compare_facts(claim_text, snippet)
    rank = {"hit": 30, "partial": 15, "none": 0}.get(compared["status"], 0)
    if official:
        rank += 8
    _, para_score = pick_paragraph(claim_text, snippet)
    return rank + para_score, compared


def _live_cards(diseases: list[str], claim_text: str, enabled: bool = False) -> list[dict[str, Any]]:
    if not enabled or os.environ.get("TNB_FAST", "0") == "1":
        return []
    try:
        from live_pages import live_event_cards

        return live_event_cards(diseases, claim_text, limit=4)
    except Exception:
        return []


def _corpus_matches(
    claim_text: str,
    item: dict[str, Any],
    corpus: list[dict[str, Any]] | None,
    sources: dict[str, dict[str, Any]] | None,
    *,
    deep: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    official: list[dict[str, Any]] = []
    peers: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    current_id = str(item.get("content_id") or "")
    current_title = _norm_title(str(item.get("title") or ""))
    claim_facts = extract_facts(claim_text)
    for row in corpus or []:
        cid = str(row.get("content_id") or "")
        if cid == current_id:
            continue
        title = str(row.get("title") or "")
        url = str(row.get("url") or "")
        if "pet-travel" in url or title.lower().startswith("http") or _norm_title(title) in {"https www aphis usda gov"}:
            continue
        key = _norm_title(title)
        if not key or key in seen_titles:
            continue
        src = (sources or {}).get(str(row.get("source_id") or ""))
        official_src = source_is_official(src, url)
        if not official_src or not deep:
            other = extract_facts(title)
            place_hit = set(other["places"]) & set(claim_facts["places"])
            dis_hit = set(other["diseases"]) & set(claim_facts["diseases"])
            animal_hit = set(other["animals"]) & set(claim_facts["animals"])
            if not (dis_hit and (place_hit or animal_hit)):
                continue
            para, score = title, 3
        else:
            para, score = pick_paragraph(claim_text, f"{title}. {row.get('text') or ''}")
            if score < 3:
                continue
        snippet = para or title
        compared = compare_facts(claim_text, snippet)
        if compared["status"] == "none" and score < 3:
            continue
        if official_src and compared["status"] == "partial":
            if not compared.get("shared_places") and set(compared.get("shared_animals") or []) <= {"fauna silvestre"}:
                continue
        seen_titles.add(key)
        packed = {
            "title": title[:140],
            "snippet": snippet[:700],
            "url": row.get("url") or None,
            "content_id": cid,
        }
        if official_src:
            official.append(packed)
        elif key != current_title:
            peers.append(packed)
        if len(official) >= 4 and len(peers) >= 8:
            break
    return official, peers


def build_review_contrast(
    claim_text: str,
    evidence_rows: list[dict[str, Any]] | None,
    *,
    item: dict[str, Any] | None = None,
    corpus: list[dict[str, Any]] | None = None,
    sources: dict[str, dict[str, Any]] | None = None,
    deep: bool = False,
) -> dict[str, Any]:
    item = item or {}
    facts = extract_facts(claim_text)
    empty = {
        "status": "none",
        "stance": None,
        "snippet": None,
        "url": None,
        "title": None,
        "why": "Esta nota no trajo una frase contrastable.",
        "facts": facts.get("labels") or [],
        "peers": [],
    }
    if not claim_text:
        return empty

    candidates: list[dict[str, Any]] = []
    for ev in evidence_rows or []:
        snippet = str(ev.get("snippet") or ev.get("text") or "").strip()
        if len(snippet) < 40:
            continue
        para, _score = pick_paragraph(claim_text, snippet)
        use = para or snippet
        rank, compared = _score_candidate(claim_text, use, True)
        if compared["status"] == "none":
            continue
        candidates.append(
            {
                "rank": rank,
                "compared": compared,
                "snippet": use[:900],
                "url": ev.get("url") or None,
                "title": ev.get("title") or None,
                "official": True,
            }
        )

    for card in _live_cards(_diseases_for(claim_text, item), claim_text):
        snippet = str(card.get("snippet") or "")
        rank, compared = _score_candidate(claim_text, snippet, True)
        if compared["status"] == "none":
            continue
        candidates.append(
            {
                "rank": rank,
                "compared": compared,
                "snippet": snippet[:900],
                "url": card.get("url"),
                "title": card.get("title"),
                "official": True,
            }
        )

    official_corpus, peers = _corpus_matches(claim_text, item, corpus, sources, deep=deep)
    for row in official_corpus:
        rank, compared = _score_candidate(claim_text, row["snippet"], True)
        if compared["status"] == "none":
            continue
        candidates.append({**row, "rank": rank, "compared": compared, "official": True})

    candidates.sort(key=lambda c: c.get("rank") or 0, reverse=True)
    best = candidates[0] if candidates else None
    peer_out = [{"title": p["title"], "content_id": p.get("content_id")} for p in peers[:6]]

    if best:
        compared = best["compared"]
        why = compared.get("why") or ""
        if compared["status"] == "partial" and peer_out:
            why += f" {len(peer_out)} nota(s) de prensa del recorte coinciden en el mismo hecho."
        return {
            "status": compared["status"],
            "stance": compared.get("stance"),
            "snippet": best.get("snippet"),
            "url": best.get("url"),
            "title": best.get("title"),
            "why": why,
            "facts": facts.get("labels") or [],
            "peers": peer_out,
        }

    if peer_out:
        return {
            "status": "peer",
            "stance": None,
            "snippet": None,
            "url": None,
            "title": None,
            "why": (
                f"{len(peer_out)} nota(s) de prensa del recorte coinciden en estos hechos. "
                "No hay boletín USDA / SENASICA / WOAH de este caso en el recorte."
            ),
            "facts": facts.get("labels") or [],
            "peers": peer_out,
        }

    return {
        "status": "none",
        "stance": None,
        "snippet": None,
        "url": None,
        "title": None,
        "why": (
            "No hay boletín oficial ni otras notas del recorte que afirmen, desmientan "
            "o contradigan estos hechos."
        ),
        "facts": facts.get("labels") or [],
        "peers": [],
    }


def attach_review_contrast(
    item: dict[str, Any],
    claims: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    *,
    corpus: list[dict[str, Any]] | None = None,
    sources: dict[str, dict[str, Any]] | None = None,
    deep: bool = False,
) -> dict[str, Any]:
    claim_text = pick_review_claim(claims, str(item.get("title") or ""))
    contrast = build_review_contrast(
        claim_text, evidence, item=item, corpus=corpus, sources=sources, deep=deep
    )
    item["primary_claim"] = claim_text or None
    item["evidence_snippet"] = contrast.get("snippet")
    item["contrast"] = contrast
    return item
