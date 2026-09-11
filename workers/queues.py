"""Colas: ingest, nlp, image, embedding, evidence, narrative.

Redis si REDIS_URL está vivo; si no, queue.Queue in-process.
El dispatcher del pipeline drena image para que OCR no bloquee la ingesta.
"""
from __future__ import annotations

import json
import os
import queue
from typing import Any, Callable

QUEUE_INGEST = "tnb:ingest"
QUEUE_NLP = "tnb:nlp"
QUEUE_IMAGE = "tnb:image"
QUEUE_EMBEDDING = "tnb:embedding"
QUEUE_EVIDENCE = "tnb:evidence"
QUEUE_NARRATIVE = "tnb:narrative"

QUEUES = (
    QUEUE_INGEST,
    QUEUE_NLP,
    QUEUE_IMAGE,
    QUEUE_EMBEDDING,
    QUEUE_EVIDENCE,
    QUEUE_NARRATIVE,
)

_LOCAL: dict[str, queue.Queue] = {name: queue.Queue() for name in QUEUES}


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _redis():
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url(), decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def enqueue(queue_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if queue_name not in QUEUES:
        raise ValueError(f"cola desconocida: {queue_name}")
    client = _redis()
    if client is not None:
        client.lpush(queue_name, json.dumps(payload, ensure_ascii=False))
        return {"queued": True, "queue": queue_name, "backend": "redis"}
    _LOCAL[queue_name].put(payload)
    return {"queued": True, "queue": queue_name, "backend": "memory"}


def pop(queue_name: str, timeout: int = 1) -> dict[str, Any] | None:
    client = _redis()
    if client is not None:
        item = client.brpop(queue_name, timeout=timeout)
        if not item:
            return None
        _q, raw = item
        return json.loads(raw)
    try:
        return _LOCAL[queue_name].get(timeout=timeout)
    except queue.Empty:
        return None


def drain(queue_name: str, handler: Callable[[dict[str, Any]], Any], limit: int = 500) -> list[Any]:
    results = []
    for _ in range(limit):
        if _LOCAL[queue_name].empty() and _redis() is None:
            break
        payload = pop(queue_name, timeout=0)
        if payload is None:
            break
        results.append(handler(payload))
    return results


def qsize(queue_name: str) -> int:
    return _LOCAL[queue_name].qsize()


def worker_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    return {"worker": "ingest", "status": "queued", "payload_keys": list(payload)}


def worker_nlp(payload: dict[str, Any]) -> dict[str, Any]:
    from claims import extract_claims
    from entities import extract_entities
    from relevance import classify_topic

    text = payload.get("text") or ""
    return {
        "worker": "nlp",
        "status": "ok",
        "relevance": classify_topic(text),
        "entities": extract_entities(text),
        "claims": extract_claims(text),
    }


def worker_image(payload: dict[str, Any]) -> dict[str, Any]:
    from process import process_image

    return process_image(
        payload.get("url") or "",
        alt_text=payload.get("alt_text") or "",
        content_id=payload.get("content_id") or "",
        known_phashes=payload.get("known_phashes") or [],
    ) or {"ok": False, "error": "download_failed", "url": payload.get("url")}


def worker_embedding(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text") or ""
    # MVP: hash estable como placeholder de embedding (pgvector en fases posteriores)
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vector = [b / 255.0 for b in digest[:24]]
    return {
        "worker": "embedding",
        "status": "ok",
        "model_version": "hash_placeholder_v1",
        "dim": len(vector),
        "vector": vector,
    }


def worker_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    from retrieve import retrieve_evidence
    from nli import verify_claim

    claim = payload.get("claim") or payload.get("text") or ""
    evidence = retrieve_evidence(claim)
    nli = verify_claim(claim, evidence)
    return {"worker": "evidence", "status": "ok", "evidence": evidence, "nli": nli}


def worker_narrative(payload: dict[str, Any]) -> dict[str, Any]:
    from engine import cluster_claims

    return {"worker": "narrative", "status": "ok", **cluster_claims(payload.get("claims") or [])}


WORKERS = {
    QUEUE_INGEST: worker_ingest,
    QUEUE_NLP: worker_nlp,
    QUEUE_IMAGE: worker_image,
    QUEUE_EMBEDDING: worker_embedding,
    QUEUE_EVIDENCE: worker_evidence,
    QUEUE_NARRATIVE: worker_narrative,
}


def dispatch(queue_name: str, payload: dict[str, Any]) -> Any:
    enqueue(queue_name, payload)
    return WORKERS[queue_name](payload)
