"""Ingesta RSS — httpx + ElementTree. Extrae título, link, summary e imágenes."""
from __future__ import annotations

import os
import re
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from access import USER_AGENT, polite_delay, resolve_access
from dedup import DedupIndex
from normalize import UniversalContent, extract_img_refs, to_universal
from source_catalog import active_sources

HEADERS = {"User-Agent": USER_AGENT}
ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"

_IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if el.text:
        return el.text.strip()
    return "".join(el.itertext()).strip()


def _child(item: ET.Element, name: str) -> ET.Element | None:
    for child in list(item):
        if _local(child.tag).lower() == name.lower():
            return child
    return None


def _looks_image(url: str, mime: str = "") -> bool:
    u = (url or "").lower().split("?")[0]
    if mime.lower().startswith("image/"):
        return True
    return any(u.endswith(ext) for ext in _IMG_EXT)


def _image_urls(item: ET.Element) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    alts: list[str] = []
    for child in list(item.iter()):
        tag = _local(child.tag).lower()
        if tag == "enclosure":
            url = (child.get("url") or "").strip()
            typ = child.get("type") or ""
            if url and _looks_image(url, typ):
                urls.append(url)
        elif tag in {"content", "thumbnail"}:
            url = (child.get("url") or "").strip()
            if url and (_looks_image(url, child.get("type") or "") or tag == "thumbnail"):
                urls.append(url)
                alts.append(child.get("title") or child.get("alt") or "")
    html_blobs = [
        _text(_child(item, "description")),
        _text(_child(item, "summary")),
        _text(_child(item, "encoded")),
    ]
    for blob in html_blobs:
        for src, alt in extract_img_refs(blob):
            urls.append(src)
            alts.append(alt)
    seen: set[str] = set()
    out_urls: list[str] = []
    out_alts: list[str] = []
    for i, url in enumerate(urls):
        if url in seen:
            continue
        seen.add(url)
        out_urls.append(url)
        out_alts.append(alts[i] if i < len(alts) else "")
    return out_urls, out_alts


def _rss_item_limit(explicit: int | None = None) -> int:
    if explicit is not None:
        return max(1, int(explicit))
    try:
        return max(1, int(os.environ.get("TNB_RSS_LIMIT", "40")))
    except ValueError:
        return 40


def parse_rss(xml_text: str, source_id: str, limit: int | None = None) -> list[UniversalContent]:
    limit = _rss_item_limit(limit)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items: list[UniversalContent] = []
    nodes = list(root.findall(".//item"))
    if not nodes:
        nodes = list(root.findall(f".//{ATOM}entry")) or [
            el for el in root.iter() if _local(el.tag) == "entry"
        ]

    for item in nodes[:limit]:
        title = _text(_child(item, "title"))
        link_el = _child(item, "link")
        link = _text(link_el)
        if not link and link_el is not None:
            link = (link_el.get("href") or "").strip()
        desc = (
            _text(_child(item, "description"))
            or _text(_child(item, "summary"))
            or _text(_child(item, "encoded"))
            or _text(_child(item, "content"))
        )
        pub = (
            _text(_child(item, "pubDate"))
            or _text(_child(item, "published"))
            or _text(_child(item, "updated"))
            or _text(_child(item, "date"))
        )
        author = _text(_child(item, "author")) or _text(_child(item, "creator"))
        images, alts = _image_urls(item)
        if not link:
            continue
        items.append(
            to_universal(
                source_id=source_id,
                url=link,
                title=title,
                text=re.sub(r"<[^>]+>", " ", desc),
                images=images,
                image_alts=alts,
                author=author,
                published_at=pub or None,
                raw_format="rss",
            )
        )
    return items


def fetch_source_rss(
    source: dict[str, Any],
    timeout: float = 20.0,
    delay: bool = True,
    limit: int | None = None,
) -> list[UniversalContent]:
    if resolve_access(source) != "rss" or not source.get("rss_url"):
        return []
    if delay:
        polite_delay(source)
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(source["rss_url"])
        response.raise_for_status()
        items = parse_rss(response.text, source["source_id"], limit=limit)
    from html_fetcher import enrich_rss_items

    return enrich_rss_items(items, source)


def fetch_due_rss(dedup: DedupIndex | None = None) -> dict[str, Any]:
    index = dedup or DedupIndex()
    collected: list[dict[str, Any]] = []
    skipped = 0
    errors: list[dict[str, str]] = []
    for source in active_sources():
        if resolve_access(source) != "rss":
            continue
        try:
            for item in fetch_source_rss(source):
                is_dup, reason = index.register(item.url, f"{item.title} {item.text}")
                if is_dup:
                    skipped += 1
                    continue
                collected.append(item.to_dict())
        except Exception as exc:  # noqa: BLE001 — un feed no tumba el ciclo
            errors.append({"source_id": source["source_id"], "error": str(exc)})
    return {
        "count": len(collected),
        "skipped_duplicates": skipped,
        "items": collected,
        "errors": errors,
    }
