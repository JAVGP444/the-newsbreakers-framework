"""UniversalContent — esquema canónico de un artículo recolectado.

content_id: CNT-{12 hex}  (estable por URL si se pasa url_sha256)
RAW se guarda aparte (JSONL / Mongo); esto es PROCESSED (SQLite / Postgres).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dedup import text_sha256, url_sha256
from safe_urls import stored_article_url


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_content_id(url: str | None = None) -> str:
    if url:
        return f"CNT-{url_sha256(url)[:12]}"
    return f"CNT-{uuid4().hex[:12]}"


def strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_img_refs(html: str) -> list[tuple[str, str]]:
    """Pares (src, alt) desde HTML de descripción RSS."""
    refs: list[tuple[str, str]] = []
    for tag in re.finditer(r"<img\b[^>]*>", html or "", flags=re.I):
        chunk = tag.group(0)
        src_m = re.search(r"""src\s*=\s*["']([^"']+)["']""", chunk, flags=re.I)
        alt_m = re.search(r"""alt\s*=\s*["']([^"']*)["']""", chunk, flags=re.I)
        if src_m:
            refs.append((src_m.group(1).strip(), alt_m.group(1).strip() if alt_m else ""))
    return refs


@dataclass
class UniversalContent:
    content_id: str
    source_id: str
    url: str
    title: str = ""
    text: str = ""
    images: list[str] = field(default_factory=list)
    image_alts: list[str] = field(default_factory=list)
    author: str = ""
    published_at: str | None = None
    collected_at: str = ""
    language: str = "und"
    url_sha256: str = ""
    text_sha256: str = ""
    pipeline_level: int = 0
    raw_format: str = "rss"  # rss | api | html | fixture
    model_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def to_universal(
    *,
    source_id: str,
    url: str,
    title: str = "",
    text: str = "",
    images: list[str] | None = None,
    image_alts: list[str] | None = None,
    author: str = "",
    published_at: str | None = None,
    language: str = "und",
    raw_format: str = "rss",
    pipeline_level: int = 1,
) -> UniversalContent:
    url = stored_article_url((url or "").strip())
    title = re.sub(r"\s+", " ", (title or "").strip())
    body = strip_html(text)
    collected = _now_iso()
    imgs = list(images or [])
    alts = list(image_alts or [])
    if not imgs:
        refs = extract_img_refs(text)
        imgs = [src for src, _alt in refs]
        alts = [alt for _src, alt in refs]
    if url:
        content_id = make_content_id(url)
        uhash = url_sha256(url)
    else:
        digest = hashlib.sha256((title or body or "inapp").encode("utf-8")).hexdigest()
        content_id = "CNT-" + digest[:12]
        uhash = digest
    return UniversalContent(
        content_id=content_id,
        source_id=source_id,
        url=url,
        title=title,
        text=body,
        images=imgs,
        image_alts=alts,
        author=author,
        published_at=published_at,
        collected_at=collected,
        language=language,
        url_sha256=uhash,
        text_sha256=text_sha256(f"{title} {body}"),
        pipeline_level=pipeline_level,
        raw_format=raw_format,
        model_versions={"normalizer": "universal_v1"},
    )
