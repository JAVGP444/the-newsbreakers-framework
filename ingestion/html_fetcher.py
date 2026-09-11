"""Cuerpo completo de artículos RSS: httpx + BeautifulSoup.

Solo se llama para ítems ya obtenidos por RSS/API. No scrapea fuentes
HTML-only (scrape deferred). Respeta robots.txt y timeouts.
"""
from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from access import USER_AGENT, robots_allowed
from dedup import text_sha256
from normalize import UniversalContent, extract_img_refs, strip_html

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 12.0
MIN_RSS_CHARS = 480
MAX_BODY_CHARS = 20000
MAX_FETCH_PER_SOURCE = 8

_MAIN_SELECTORS = (
    "article",
    "main",
    "[role='main']",
    ".article-body",
    ".entry-content",
    ".post-content",
    ".news-article",
    ".c-article-body",
    "#content",
    ".content",
)


def _soup(html: str):
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser")
    except Exception:
        return None


def extract_main_text(html: str, base_url: str = "") -> dict[str, Any]:
    """Extrae título, cuerpo e imágenes del HTML. Sin BeautifulSoup usa regex."""
    soup = _soup(html)
    title = ""
    images: list[str] = []
    alts: list[str] = []
    if soup is not None:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
            tag.decompose()
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            title = str(og["content"]).strip() or title
        node = None
        for selector in _MAIN_SELECTORS:
            node = soup.select_one(selector)
            if node and len(node.get_text(" ", strip=True)) > 200:
                break
            node = None
        if node is None:
            node = soup.body or soup
        text = node.get_text(" ", strip=True) if node else ""
        for img in (node or soup).find_all("img")[:8]:
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/") and base_url:
                src = urljoin(base_url, src)
            if src.startswith("http"):
                images.append(src)
                alts.append(img.get("alt") or "")
    else:
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html or "", flags=re.I)
        title = title_m.group(1).strip() if title_m else ""
        text = strip_html(html)
        for src, alt in extract_img_refs(html):
            images.append(src)
            alts.append(alt)
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > MAX_BODY_CHARS:
        text = text[:MAX_BODY_CHARS].rsplit(" ", 1)[0]
    return {"title": title, "text": text, "images": images, "image_alts": alts}


def fetch_article_html(url: str, timeout: float = TIMEOUT) -> dict[str, Any] | None:
    if not url or not url.startswith("http"):
        return None
    host = (urlparse(url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return None
    if os.environ.get("TNB_FAST", "0") == "1":
        return None
    if not robots_allowed(url):
        return {"ok": False, "url": url, "error": "robots_disallow"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
            response = client.get(url)
            if response.status_code == 404:
                return {"ok": False, "url": url, "error": "404"}
            response.raise_for_status()
            ctype = (response.headers.get("content-type") or "").lower()
            if "html" not in ctype and "xml" not in ctype and not url.endswith(".html"):
                return {"ok": False, "url": url, "error": f"content-type {ctype}"}
            extracted = extract_main_text(response.text, base_url=str(response.url))
            extracted["ok"] = True
            extracted["url"] = str(response.url)
            extracted["status"] = response.status_code
            return extracted
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def enrich_rss_items(items: list[UniversalContent], source: dict[str, Any] | None = None) -> list[UniversalContent]:
    """Completa el cuerpo si el RSS solo trae un summary corto."""
    if os.environ.get("TNB_FAST", "0") == "1":
        return items
    method = str((source or {}).get("access_method") or "rss").lower()
    if method not in {"rss", "api"}:
        return items
    fetched = 0
    for item in items:
        if fetched >= MAX_FETCH_PER_SOURCE:
            break
        if len(item.text or "") >= MIN_RSS_CHARS:
            continue
        page = fetch_article_html(item.url)
        if not page or not page.get("ok"):
            continue
        body = str(page.get("text") or "").strip()
        if len(body) <= len(item.text or ""):
            continue
        item.text = body
        item.text_sha256 = text_sha256(f"{item.title} {item.text}")
        item.raw_format = "rss"
        item.model_versions = {**(item.model_versions or {}), "body": "html_fetcher_v1"}
        extra_imgs = [u for u in (page.get("images") or []) if u not in item.images]
        extra_alts = list(page.get("image_alts") or [])
        for i, url in enumerate(extra_imgs[:4]):
            item.images.append(url)
            item.image_alts.append(extra_alts[i] if i < len(extra_alts) else "")
        fetched += 1
    return items
