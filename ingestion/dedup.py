"""Deduplicación en cascada (embudo niveles 0–1).

Orden:
  1. URL exacta (existe en índice / SQLite)
  2. SHA-256(url)
  3. SHA-256(texto normalizado)
  4. Similitud semántica (pgvector más adelante; stub = False)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def url_sha256(url: str) -> str:
    return hashlib.sha256((url or "").strip().encode("utf-8")).hexdigest()


def text_sha256(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_duplicate_url(url: str, seen_hashes: set[str]) -> bool:
    return url_sha256(url) in seen_hashes


def semantic_similar(_a: str, _b: str, _threshold: float = 0.92) -> bool:
    """Fase posterior: embeddings + pgvector. MVP = False."""
    return False


@dataclass
class DedupIndex:
    urls: set[str] = field(default_factory=set)
    url_hashes: set[str] = field(default_factory=set)
    text_hashes: set[str] = field(default_factory=set)

    def check(self, url: str, text: str = "") -> tuple[bool, str]:
        url = (url or "").strip()
        if url and url in self.urls:
            return True, "url"
        if url:
            uhash = url_sha256(url)
            if uhash in self.url_hashes:
                return True, "url_sha256"
        if text:
            thash = text_sha256(text)
            if thash in self.text_hashes:
                return True, "text_sha256"
            if semantic_similar(text, ""):
                return True, "semantic"
        return False, ""

    def add(self, url: str, text: str = "") -> None:
        url = (url or "").strip()
        if url:
            self.urls.add(url)
            self.url_hashes.add(url_sha256(url))
        if text:
            self.text_hashes.add(text_sha256(text))

    def register(self, url: str, text: str = "") -> tuple[bool, str]:
        dup, reason = self.check(url, text)
        if not dup:
            self.add(url, text)
        return dup, reason

    @classmethod
    def from_store(cls, store: Any) -> "DedupIndex":
        urls, url_hashes, text_hashes = store.load_dedup_hashes()
        return cls(urls=set(urls), url_hashes=set(url_hashes), text_hashes=set(text_hashes))
