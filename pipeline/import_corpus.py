"""Importa corpus real del Generador (SQLite + dashboard) hacia tnb.db."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import GENERADOR_SQLITE, IMAGES_DIR, SALIDA_DIR, ensure_paths  # noqa: E402

ensure_paths()

from dedup import DedupIndex  # noqa: E402
from normalize import to_universal  # noqa: E402
from safe_urls import is_fake_url, public_http_url  # noqa: E402
from process import write_class_png  # noqa: E402

NEWS_TYPES = {
    "Prensa",
    "Oficial nacional",
    "Oficial internacional",
    "Medio veterinario",
    "Oficial",
    "news",
    "official",
    "press",
}

TYPE_TO_VISION = {
    "youtube": "SOCIAL_MEDIA",
    "social": "SOCIAL_MEDIA",
    "oficial": "OFFICIAL_DOCUMENT",
    "oficial nacional": "OFFICIAL_DOCUMENT",
    "oficial internacional": "OFFICIAL_DOCUMENT",
    "investigación": "INFOGRAPHIC",
    "investigacion": "INFOGRAPHIC",
    "prensa": "NEWS_SCREENSHOT",
    "medio veterinario": "ANIMAL_HEALTH_CONTENT",
}


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
    except Exception:
        pass
    return [str(value)]


def _country_from_text(text: str) -> str:
    lower = (text or "").lower()
    mapping = [
        ("méxico", "MX"),
        ("mexico", "MX"),
        ("jalisco", "MX"),
        ("chiapas", "MX"),
        ("united states", "US"),
        ("estados unidos", "US"),
        ("guatemala", "GT"),
        ("brasil", "BR"),
        ("argentina", "AR"),
        ("colombia", "CO"),
        ("españa", "ES"),
        ("china", "CN"),
        ("woah", "INT"),
        ("fao", "INT"),
        ("who.int", "INT"),
    ]
    for needle, code in mapping:
        if needle in lower:
            return code
    return "INT"


def _source_id_for(url: str, raw_format: str) -> str:
    host = (urlparse(url).netloc or raw_format or "corpus").lower().replace("www.", "")
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")[:28] or "corpus"
    return f"SRC-{slug.upper()}"


def _vision_label(source_type: str, raw_format: str) -> str:
    key = (source_type or raw_format or "").lower()
    return TYPE_TO_VISION.get(key, "PHOTOGRAPH")


def load_generador_rows(limit_news: int = 90, limit_social: int = 40) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if GENERADOR_SQLITE.is_file():
        conn = sqlite3.connect(str(GENERADOR_SQLITE))
        conn.row_factory = sqlite3.Row
        docs = conn.execute(
            """
            SELECT url, title, clean_text, html_snippet, source_type, language,
                   published_at, fetched_at, disease_tags
            FROM documents
            WHERE status='active' AND url LIKE 'http%'
              AND url NOT LIKE '%example.com%'
              AND url NOT LIKE '%example.invalid%'
              AND url NOT LIKE '%social.local%'
            ORDER BY CASE WHEN url LIKE '%openalex.org%' THEN 1 ELSE 0 END, fetched_at DESC
            """
        ).fetchall()
        kept = 0
        openalex = 0
        for doc in docs:
            url = doc["url"] or ""
            if is_fake_url(url) or not str(url).startswith("http"):
                continue
            title = (doc["title"] or "").strip()
            if not title or len(title) < 8:
                continue
            is_oa = "openalex.org" in url
            if is_oa:
                if openalex >= 25:
                    continue
                openalex += 1
            elif kept >= limit_news:
                continue
            else:
                kept += 1
            text = (doc["clean_text"] or doc["html_snippet"] or title).strip()
            rows.append(
                {
                    "url": url,
                    "title": title,
                    "text": text[:2500] or title,
                    "source_type": doc["source_type"] or ("Investigación" if is_oa else "Prensa"),
                    "language": doc["language"] or "es",
                    "published_at": doc["published_at"],
                    "disease_tags": _json_list(doc["disease_tags"]),
                    "raw_format": "corpus",
                    "country": _country_from_text(f"{title} {text} {url}"),
                }
            )
        for yt in conn.execute("SELECT * FROM youtube_videos").fetchall():
            vid = yt["video_id"]
            url = public_http_url(yt["url"] or "") or (
                f"https://www.youtube.com/watch?v={vid}" if vid else ""
            )
            if not url:
                continue
            title = (yt["title"] or f"YouTube {vid}").strip()
            text = " ".join(
                p for p in (title, yt["description"] or "", yt["transcript_text"] or "", " ".join(_json_list(yt["disease_tags"])))
                if p and p != "None"
            )
            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
            rows.append(
                {
                    "url": url,
                    "title": title,
                    "text": text[:2500],
                    "source_type": "YouTube",
                    "language": "es",
                    "published_at": yt["published_at"],
                    "disease_tags": _json_list(yt["disease_tags"]),
                    "raw_format": "youtube",
                    "country": "MX",
                    "images": [thumb],
                    "image_alts": [title],
                }
            )
        social_n = 0
        for sig in conn.execute("SELECT * FROM social_signals ORDER BY created_at DESC").fetchall():
            if social_n >= limit_social:
                break
            content = (sig["content"] or "").strip()
            real = public_http_url(sig["url"] or "")
            if not content:
                continue
            social_n += 1
            sid = sig["signal_id"]
            rows.append(
                {
                    "url": real or f"inapp:social/{sid}",
                    "title": content[:140],
                    "text": content,
                    "source_type": sig["platform"] or "social",
                    "language": "es",
                    "published_at": sig["published_at"],
                    "disease_tags": _json_list(sig["disease_tags"]),
                    "raw_format": "social",
                    "country": _country_from_text(content),
                }
            )
        conn.close()
        return rows

    # Fallback: dashboard HTML
    html = SALIDA_DIR / "urls_enfermedades_dashboard.html"
    if not html.is_file():
        return rows
    text = html.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"const DATA = (\{.*?\});\s*\n", text)
    if not m:
        return rows
    data = json.loads(m.group(1))
    for doc in (data.get("documents") or [])[:limit_news]:
        url = doc.get("url") or ""
        if is_fake_url(url) or not str(url).startswith("http"):
            continue
        rows.append(
            {
                "url": url,
                "title": doc.get("titulo") or url,
                "text": doc.get("texto") or doc.get("titulo") or "",
                "source_type": doc.get("tipo_fuente") or "Prensa",
                "language": "es",
                "published_at": doc.get("fecha"),
                "disease_tags": doc.get("enfermedad_ids") or [],
                "raw_format": "corpus",
                "country": doc.get("pais") or "XX",
            }
        )
    return rows


def corpus_to_universal(row: dict[str, Any], index: int) -> Any:
    images = list(row.get("images") or [])
    alts = list(row.get("image_alts") or [])
    if not images:
        label = _vision_label(str(row.get("source_type") or ""), str(row.get("raw_format") or ""))
        path = IMAGES_DIR / f"corpus_{hashlib.sha256(row['url'].encode()).hexdigest()[:12]}.png"
        write_class_png(path, label, seed=index)
        images = [str(path)]
        alts = [label]
    item = to_universal(
        source_id=_source_id_for(row["url"], row.get("raw_format") or "corpus"),
        url=row["url"],
        title=row.get("title") or "",
        text=row.get("text") or "",
        images=images,
        image_alts=alts,
        published_at=str(row.get("published_at") or "") or None,
        language=row.get("language") or "es",
        raw_format=row.get("raw_format") or "corpus",
    )
    payload = item.to_dict()
    payload["country"] = row.get("country")
    payload["source_type"] = row.get("source_type")
    payload["disease_tags"] = row.get("disease_tags") or []
    return payload


def inject_corpus(store: Any, index: DedupIndex, *, limit_news: int = 90) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for i, row in enumerate(load_generador_rows(limit_news=limit_news)):
        payload = corpus_to_universal(row, i)
        dup, _reason = index.register(payload["url"], f"{payload.get('title')} {payload.get('text')}")
        if dup:
            continue
        created.append(payload)
    store.audit("cycle", "corpus", "generador_import", {"count": len(created)})
    return created
