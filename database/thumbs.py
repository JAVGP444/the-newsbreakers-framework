"""Miniaturas reales de artículos — foto del documento o tarjeta de contenido.

Prioridad:
  1. YouTube hqdefault
  2. og:image / twitter:image / primera <img> útil del HTML
  3. Foto local ya descargada (nunca placeholders, dataset CNN, fb_/demo_seed)
  4. Tarjeta PIL con título, fuente y extracto (no mascotas de enfermedad)

Archivo canónico: storage/images/thumbs/{content_id}.jpg
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

from bootstrap import FRAMEWORK_ROOT, IMAGES_DIR

_ing = str(FRAMEWORK_ROOT / "ingestion")
if _ing not in sys.path:
    sys.path.insert(0, _ing)
from access import USER_AGENT  # noqa: E402

THUMBS_DIR = IMAGES_DIR / "thumbs"
HTML_TIMEOUT = 4.0
IMAGE_TIMEOUT = 6.0
FAVICON_TIMEOUT = 2.0
MIN_IMAGE_BYTES = 800
MAX_IMAGE_BYTES = 6 * 1024 * 1024
CARD_W, CARD_H = 800, 450

_YT = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})",
    re.I,
)
_SKIP_IMG = re.compile(
    r"(logo|sprite|pixel|tracking|1x1|spacer|blank\.gif|placeholder|default[-_]?(og|share)|avatar|icon[-_])",
    re.I,
)
_HOST_NAMES = {
    "linkedin.com": "LinkedIn",
    "www.linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "www.facebook.com": "Facebook",
    "m.facebook.com": "Facebook",
    "twitter.com": "Twitter",
    "x.com": "Twitter",
    "www.x.com": "Twitter",
    "pubmed.ncbi.nlm.nih.gov": "PubMed",
    "ncbi.nlm.nih.gov": "PubMed",
    "youtube.com": "YouTube",
    "www.youtube.com": "YouTube",
    "m.youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "reddit.com": "Reddit",
    "www.reddit.com": "Reddit",
    "instagram.com": "Instagram",
    "www.instagram.com": "Instagram",
}
_NO_OG_HOSTS = (
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
)

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_favicon_cache: dict[str, Any] = {}


def thumbs_dir() -> Path:
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    return THUMBS_DIR


def safe_content_id(content_id: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9._-]+", "_", str(content_id or "").strip())[:80]
    return raw or hashlib.sha256(str(content_id).encode()).hexdigest()[:16]


def thumb_path_for(content_id: str) -> Path:
    return thumbs_dir() / f"{safe_content_id(content_id)}.jpg"


def youtube_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _YT.search(str(url))
    return match.group(1) if match else None


def youtube_thumb_url(url: str | None) -> str | None:
    vid = youtube_id(url)
    return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg" if vid else None


def is_generic_visual(path_or_url: str | None, mime: str = "") -> bool:
    """True = no usar como preview (placeholders, CNN sintético, seeds)."""
    raw = str(path_or_url or "").replace("\\", "/")
    blob = f"{raw} {mime}".lower()
    name = Path(raw).name.lower()
    if not raw.strip():
        return True
    if name.startswith("ph_") or name.endswith(".svg") or "image/svg" in blob:
        return True
    if "models/cnn" in blob or "cnn/dataset" in blob:
        return True
    if name.startswith("fb_") or name.startswith("corpus_") or "demo_seed" in name:
        return True
    if "/fb_" in blob or "/corpus_" in blob or "demo_seed" in blob:
        return True
    return False


def is_pil_content_card(path: str | Path | None) -> bool:
    """True = tarjeta PIL 800×450 (barra cian), no foto de noticia."""
    if not path:
        return False
    file = Path(path)
    if not file.is_file():
        return False
    try:
        from PIL import Image

        with Image.open(file) as img:
            if img.size != (CARD_W, CARD_H):
                return False
            rgb = img.convert("RGB")
            bar = rgb.getpixel((10, 2))
            return bar[0] < 90 and bar[1] > 150 and bar[2] > 180
    except Exception:
        return False


def is_real_photo_file(path: str | Path | None, mime: str = "") -> bool:
    """JPEG/PNG descargado (YouTube, og:image, foto de artículo), nunca dibujo CNN ni tarjeta PIL."""
    if not path:
        return False
    file = Path(path)
    if not file.is_file() or is_generic_visual(str(file), mime) or is_pil_content_card(file):
        return False
    if file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return False
    try:
        if file.stat().st_size < 4000:
            return False
    except OSError:
        return False
    try:
        from PIL import Image

        with Image.open(file) as img:
            w, h = img.size
        if w <= 64 or h <= 64:
            return False
    except Exception:
        return False
    return True


def _sample_origin(article: dict[str, Any] | None, store: Any | None = None) -> str:
    if not article:
        return "noticia"
    if youtube_id(article.get("url")):
        return "YouTube"
    name = source_display_name(article, store)
    return name or "noticia"


def list_real_photo_samples(store: Any, limit: int = 12) -> list[dict[str, Any]]:
    """Miniaturas reales del observatorio para el laboratorio CNN. Nunca dibujos sintéticos."""
    cap = max(1, min(int(limit or 12), 24))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(sample: dict[str, Any]) -> None:
        sid = str(sample.get("id") or "")
        if not sid or sid in seen or len(out) >= cap:
            return
        seen.add(sid)
        out.append(sample)

    def from_article(article: dict[str, Any], path: Path, kind: str) -> None:
        cid = str(article.get("content_id") or "").strip()
        title = re.sub(r"\s+", " ", str(article.get("title") or "")).strip()
        if not cid or not title:
            return
        add(
            {
                "id": cid,
                "kind": kind,
                "content_id": cid,
                "title": title[:160],
                "label_es": title[:90],
                "url": f"/thumbs/{cid}",
                "origin": _sample_origin(article, store),
                "class": "PHOTOGRAPH",
            }
        )

    try:
        videos = store.list_by_format("youtube", limit=40)
    except Exception:
        videos = []
    yt_slots = min(8, cap)
    for art in videos or []:
        if len(out) >= yt_slots:
            break
        cid = str(art.get("content_id") or "")
        path = thumb_path_for(cid)
        if is_real_photo_file(path):
            from_article(art, path, "thumb")
            continue
        local = _local_photo(store, cid)
        if local is not None and is_real_photo_file(local):
            from_article(art, local, "image")

    thumbs = []
    try:
        thumbs = sorted(thumbs_dir().glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        thumbs = []
    for path in thumbs:
        if len(out) >= cap:
            break
        if not is_real_photo_file(path):
            continue
        cid = path.stem
        art = None
        try:
            art = store.resolve_article(cid) or store.get_article(cid)
        except Exception:
            art = None
        if not art:
            continue
        from_article(art, path, "thumb")

    if len(out) < cap:
        try:
            rows = store.list_images()
        except Exception:
            rows = []
        for row in rows or []:
            if len(out) >= cap:
                break
            if not getattr(store, "is_news_thumb", lambda _r: False)(row):
                continue
            key = Path(str(row.get("storage_key") or ""))
            path = key if key.is_file() else IMAGES_DIR / key.name
            if not is_real_photo_file(path, str(row.get("mime_type") or "")):
                continue
            cid = str(row.get("content_id") or "")
            art = None
            try:
                art = store.get_article(cid) if cid else None
            except Exception:
                art = None
            if art:
                from_article(art, path, "image")

    return out


def resolve_real_sample(store: Any, sample_id: str) -> tuple[Path | None, str, dict[str, Any] | None]:
    """Resuelve una muestra real (thumb o foto minada). Nunca models/cnn/samples."""
    safe = Path(str(sample_id or "")).name
    if not safe or is_generic_visual(safe):
        return None, "", None
    stem = Path(safe).stem
    art = None
    try:
        art = store.resolve_article(stem) or store.resolve_article(safe)
    except Exception:
        art = None
    if art:
        cid = str(art.get("content_id") or "")
        page_url = str(art.get("url") or "")
        thumb = thumb_path_for(cid)
        if is_real_photo_file(thumb):
            return thumb, page_url, art
        local = _local_photo(store, cid)
        if local is not None and is_real_photo_file(local):
            return local, page_url, art
    row = None
    try:
        row = store.get_image(safe) or store.get_image(stem)
    except Exception:
        row = None
    if row:
        key = Path(str(row.get("storage_key") or ""))
        path = key if key.is_file() else IMAGES_DIR / key.name
        if is_real_photo_file(path, str(row.get("mime_type") or "")):
            cid = str(row.get("content_id") or "")
            art2 = None
            try:
                art2 = store.get_article(cid) if cid else None
            except Exception:
                art2 = None
            page_url = str((art2 or {}).get("url") or row.get("source_url") or "")
            return path, page_url, art2
    for candidate in (thumbs_dir() / safe, thumbs_dir() / f"{stem}.jpg"):
        if is_real_photo_file(candidate):
            return candidate, "", None
    return None, "", None


def source_display_name(article: dict[str, Any], store: Any | None = None) -> str:
    url = str(article.get("url") or "")
    host = ""
    if url.startswith("http://") or url.startswith("https://"):
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            host = ""
    if host in _HOST_NAMES:
        return _HOST_NAMES[host]
    if host:
        for suffix, label in _HOST_NAMES.items():
            if host == suffix or host.endswith("." + suffix):
                return label
    if store is not None:
        src = store.get_source(article.get("source_id") or "")
        name = (src or {}).get("name") or ""
        if name and not str(name).upper().startswith("SRC-"):
            return str(name)
    stype = str(article.get("source_type") or "").strip()
    if stype and not stype.upper().startswith("SRC-"):
        return stype
    if host:
        return host.replace("www.", "")
    return "Fuente"


def parse_preview_image_urls(html: str, base_url: str = "") -> list[str]:
    """og:image, twitter:image, luego <img src> con tamaño útil."""
    found: list[str] = []

    def add(raw: str) -> None:
        url = (raw or "").strip()
        if not url or url.startswith("data:"):
            return
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and base_url:
            url = urljoin(base_url, url)
        elif not url.startswith("http") and base_url:
            url = urljoin(base_url, url)
        if not url.startswith("http"):
            return
        if _SKIP_IMG.search(url) or url.lower().endswith(".svg"):
            return
        if url not in found:
            found.append(url)

    soup = None
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "html.parser")
    except Exception:
        soup = None

    if soup is not None:
        for key, attr in (("property", "og:image"), ("name", "twitter:image"), ("name", "twitter:image:src"), ("property", "og:image:url")):
            for tag in soup.find_all("meta", attrs={key: attr}):
                add(str(tag.get("content") or ""))
        for img in soup.find_all("img"):
            w = _int_attr(img.get("width"))
            h = _int_attr(img.get("height"))
            if (w and w < 64) or (h and h < 64):
                continue
            add(str(img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""))
    else:
        patterns = (
            r"""<meta[^>]+(?:property|name)=["']og:image(?:url)?["'][^>]+content=["']([^"']+)["']""",
            r"""<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']og:image(?:url)?["']""",
            r"""<meta[^>]+(?:property|name)=["']twitter:image(?::src)?["'][^>]+content=["']([^"']+)["']""",
            r"""<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']twitter:image(?::src)?["']""",
        )
        for pat in patterns:
            for match in re.finditer(pat, html or "", flags=re.I):
                add(match.group(1))
        for tag in re.finditer(r"<img\b[^>]*>", html or "", flags=re.I):
            chunk = tag.group(0)
            src_m = re.search(r"""(?:src|data-src)\s*=\s*["']([^"']+)["']""", chunk, flags=re.I)
            if src_m:
                add(src_m.group(1))

    return found[:8]


def _int_attr(value: Any) -> int | None:
    try:
        return int(re.sub(r"[^\d]", "", str(value or "")) or 0) or None
    except Exception:
        return None


def _lock_for(content_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(content_id)
        if lock is None:
            lock = threading.Lock()
            _locks[content_id] = lock
        return lock


def _http_get(url: str, timeout: float) -> bytes | None:
    try:
        import httpx

        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content or b""
    except Exception:
        return None


def _http_text(url: str, timeout: float) -> tuple[str, str] | None:
    try:
        import httpx

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        }
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            ctype = (response.headers.get("content-type") or "").lower()
            if "html" not in ctype and "xml" not in ctype and "text/" not in ctype:
                return None
            return str(response.url), response.text or ""
    except Exception:
        return None


def download_as_jpeg(url: str, dest: Path, timeout: float = IMAGE_TIMEOUT) -> bool:
    if is_generic_visual(url):
        return False
    data = _http_get(url, timeout)
    if not data or len(data) < MIN_IMAGE_BYTES or len(data) > MAX_IMAGE_BYTES:
        return False
    return save_bytes_as_jpeg(data, dest)


def save_bytes_as_jpeg(data: bytes, dest: Path) -> bool:
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        if img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        img.thumbnail((960, 540))
        if img.width < 40 or img.height < 40:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=85, optimize=True)
        return dest.is_file() and dest.stat().st_size > 400
    except Exception:
        return False


def copy_local_as_jpeg(src: str | Path, dest: Path) -> bool:
    path = Path(src)
    if not path.is_file() or is_generic_visual(str(path)):
        return False
    try:
        return save_bytes_as_jpeg(path.read_bytes(), dest)
    except Exception:
        return False


def _font(size: int):
    from PIL import ImageFont

    candidates = [
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = (text or "").replace("\n", " ").split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and (current not in lines or len(words) > 12):
        last = lines[-1]
        if not last.endswith("…"):
            lines[-1] = last[: max(1, len(last) - 1)].rstrip() + "…"
    return lines[:max_lines]


def _favicon_for(url: str):
    if not url.startswith("http"):
        return None
    try:
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    except Exception:
        return None
    if origin in _favicon_cache:
        return _favicon_cache[origin]
    data = _http_get(origin.rstrip("/") + "/favicon.ico", FAVICON_TIMEOUT)
    image = None
    if data and 32 < len(data) < 200_000:
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(data)).convert("RGBA")
            image.thumbnail((28, 28))
        except Exception:
            image = None
    _favicon_cache[origin] = image
    return image


def render_content_card(
    dest: Path,
    *,
    title: str,
    source: str,
    snippet: str,
    page_url: str = "",
) -> Path:
    from PIL import Image, ImageDraw

    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (CARD_W, CARD_H), (11, 17, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, CARD_W, 6), fill=(56, 189, 248))
    title_font = _font(28)
    source_font = _font(16)
    body_font = _font(18)
    pad = 36
    icon = _favicon_for(page_url) if page_url else None
    text_x = pad
    if icon is not None:
        img.paste(icon, (pad, 28), icon if icon.mode == "RGBA" else None)
        text_x = pad + icon.width + 10
    draw.text((text_x, 32), (source or "Fuente")[:48], font=source_font, fill=(148, 163, 184))
    y = 78
    for line in _wrap(draw, title or "Documento", title_font, CARD_W - pad * 2, 3):
        draw.text((pad, y), line, font=title_font, fill=(241, 245, 249))
        y += 36
    y += 12
    excerpt = re.sub(r"\s+", " ", snippet or "").strip()
    if excerpt and excerpt != (title or "").strip():
        excerpt = excerpt[:120]
        for line in _wrap(draw, excerpt, body_font, CARD_W - pad * 2, 3):
            draw.text((pad, y), line, font=body_font, fill=(203, 213, 225))
            y += 26
    img.save(dest, "JPEG", quality=88, optimize=True)
    return dest


def _snippet(article: dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", str(article.get("title") or "")).strip()
    text = re.sub(r"\s+", " ", str(article.get("text") or article.get("summary") or "")).strip()
    if not text or text == title:
        return ""
    return text[:120]


def _existing_thumb(article: dict[str, Any]) -> Path | None:
    cid = str(article.get("content_id") or "")
    dest = thumb_path_for(cid)
    if dest.is_file() and dest.stat().st_size > 400:
        return dest
    stored = str(article.get("thumb_path") or "").strip()
    if stored:
        path = Path(stored)
        if path.is_file() and path.stat().st_size > 400 and not is_generic_visual(str(path)):
            return path
    return None


def _candidate_urls(article: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    yt = youtube_thumb_url(article.get("url"))
    if yt:
        urls.append(yt)
    for raw in article.get("images") or []:
        url = str(raw or "").strip()
        if url.startswith("http") and not is_generic_visual(url):
            urls.append(url)
    return urls


def _local_photo(store: Any, content_id: str) -> Path | None:
    try:
        rows = store.list_images(content_id)
    except Exception:
        return None
    for row in rows or []:
        key = str(row.get("storage_key") or "")
        mime = str(row.get("mime_type") or "")
        src = str(row.get("source_url") or "")
        if is_generic_visual(key, mime) or is_generic_visual(src, mime):
            continue
        path = Path(key)
        if not path.is_file():
            path = IMAGES_DIR / Path(key).name
        if path.is_file() and not is_generic_visual(str(path), mime):
            return path
    return None


def _html_preview_likely(url: str) -> bool:
    if not url.startswith("http"):
        return False
    host = (urlparse(url).hostname or "").lower()
    if not host or youtube_id(url):
        return False
    return not any(host == h or host.endswith("." + h) for h in _NO_OG_HOSTS)


def _fetch_html_images(url: str, timeout: float) -> list[str]:
    if not url or not url.startswith("http"):
        return []
    host = (urlparse(url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return []
    got = _http_text(url, timeout)
    if not got:
        return []
    final_url, html = got
    return parse_preview_image_urls(html, final_url)


def _persist_thumb(store: Any, content_id: str, path: Path) -> None:
    rel = str(path)
    store.update_article_analysis(content_id, thumb_path=rel)
    row = store.get_article(content_id) or {}
    row["thumb_path"] = rel


def _allow_network() -> bool:
    return os.environ.get("TNB_FAST", "0") != "1"


def ensure_article_thumb(
    store: Any,
    article: dict[str, Any],
    *,
    fetch_html: bool | None = None,
    html_timeout: float = HTML_TIMEOUT,
) -> Path | None:
    """Garantiza un JPEG en thumbs/{id}.jpg. Nunca escribe SVG de enfermedad."""
    content_id = str(article.get("content_id") or "")
    if not content_id:
        return None
    dest = thumb_path_for(content_id)
    with _lock_for(content_id):
        existing = _existing_thumb(article)
        if existing is not None:
            if existing.resolve() != dest.resolve():
                try:
                    copy_local_as_jpeg(existing, dest)
                except Exception:
                    dest = existing
            if dest.is_file():
                _persist_thumb(store, content_id, dest)
                return dest

        if fetch_html is None:
            fetch_html = _allow_network()

        if fetch_html:
            for url in _candidate_urls(article):
                if download_as_jpeg(url, dest):
                    _persist_thumb(store, content_id, dest)
                    return dest

        local = _local_photo(store, content_id)
        if local is not None and copy_local_as_jpeg(local, dest):
            _persist_thumb(store, content_id, dest)
            return dest

        page_url = str(article.get("url") or "")
        if fetch_html and _html_preview_likely(page_url):
            for url in _fetch_html_images(page_url, html_timeout):
                if download_as_jpeg(url, dest):
                    _persist_thumb(store, content_id, dest)
                    return dest

        render_content_card(
            dest,
            title=str(article.get("title") or content_id),
            source=source_display_name(article, store),
            snippet=_snippet(article),
            page_url=page_url if fetch_html else "",
        )
        _persist_thumb(store, content_id, dest)
        return dest if dest.is_file() else None


def ensure_article_thumbs(
    store: Any,
    articles: Iterable[dict[str, Any]],
    *,
    fetch_html: bool | None = None,
    html_timeout: float = HTML_TIMEOUT,
) -> int:
    done = 0
    for article in articles:
        path = ensure_article_thumb(store, article, fetch_html=fetch_html, html_timeout=html_timeout)
        if path is not None:
            done += 1
    return done


def backfill_missing(store: Any, *, limit: int = 400, fetch_html: bool | None = None) -> int:
    rows = store.list_articles(limit=limit)
    missing = []
    for row in rows:
        path = str(row.get("thumb_path") or "")
        if path and Path(path).is_file():
            continue
        dest = thumb_path_for(row["content_id"])
        if dest.is_file():
            store.update_article_analysis(row["content_id"], thumb_path=str(dest))
            continue
        missing.append(row)
    return ensure_article_thumbs(store, missing, fetch_html=fetch_html)


if __name__ == "__main__":
    from database.store import Store

    store = Store()
    n = backfill_missing(store, limit=int(os.environ.get("TNB_THUMB_LIMIT", "400")))
    print(f"thumbs backfilled: {n}")
    store.close()
