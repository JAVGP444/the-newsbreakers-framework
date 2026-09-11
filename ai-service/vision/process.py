"""Descarga y validación de imágenes del artículo → storage/images/{sha256}.{ext}."""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from bootstrap import IMAGES_DIR
from access import USER_AGENT
from image_hash import bit_length, hamming, perceptual_hash, similarity_pct
from ocr import ocr_image
from visual_encoder import animal_health_relevance, classify_visual

MIN_BYTES = 64
MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/jpg"}


def _ext_for(mime: str, url: str) -> str:
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "png" in mime:
        return ".png"
    if "gif" in mime:
        return ".gif"
    if "webp" in mime:
        return ".webp"
    guess = Path(urlparse(url).path).suffix.lower()
    if guess in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        return ".jpg" if guess == ".jpeg" else guess
    return mimetypes.guess_extension(mime) or ".img"


def download_image(url: str, timeout: float = 15.0) -> dict[str, Any] | None:
    if not url or url.startswith("data:"):
        return None
    local = Path(url)
    if local.is_file():
        data = local.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        mime = mimetypes.guess_type(str(local))[0] or "image/png"
        ext = local.suffix or _ext_for(mime, url)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        dest = IMAGES_DIR / f"{sha}{ext}"
        if not dest.exists():
            dest.write_bytes(data)
        return {
            "ok": True,
            "url": url,
            "path": str(dest),
            "sha256": sha,
            "mime_type": mime,
            "bytes": len(data),
        }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(url)
            response.raise_for_status()
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}
    mime = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    data = response.content or b""
    if mime not in ALLOWED and not mime.startswith("image/"):
        return {"ok": False, "url": url, "error": f"content-type {mime}"}
    if len(data) < MIN_BYTES:
        return {"ok": False, "url": url, "error": "min size"}
    if len(data) > MAX_BYTES:
        return {"ok": False, "url": url, "error": "max size"}
    sha = hashlib.sha256(data).hexdigest()
    ext = _ext_for(mime or "image/jpeg", url)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGES_DIR / f"{sha}{ext}"
    if not dest.exists():
        dest.write_bytes(data)
    return {
        "ok": True,
        "url": url,
        "path": str(dest),
        "sha256": sha,
        "mime_type": mime or "image/jpeg",
        "bytes": len(data),
    }


def process_image(
    url: str,
    *,
    alt_text: str = "",
    content_id: str = "",
    known_phashes: list[tuple[str, str]] | None = None,
) -> dict[str, Any] | None:
    fetched = download_image(url)
    if not fetched or not fetched.get("ok"):
        return fetched
    path = fetched["path"]
    hashed = perceptual_hash(path)
    phash = hashed.get("phash") or ""
    reused = False
    reuse_hamming = None
    reuse_pct = None
    bits = int(hashed.get("bits") or bit_length(phash))
    for other_id, other_hash in known_phashes or []:
        pct = similarity_pct(phash, other_hash or "")
        dist = hamming(phash, other_hash or "")
        if pct >= 85.0:
            reused = True
            reuse_hamming = dist
            reuse_pct = pct
            break
    ocr = ocr_image(path, alt_text=alt_text)
    ocr_text = ocr.get("text") or alt_text or ""
    vision = classify_visual(path, url=url, ocr_text=ocr_text)
    relevance = float(vision.get("animal_health_relevance") or animal_health_relevance(f"{ocr_text} {url}"))
    image_id = f"IMG-{fetched['sha256'][:16]}"
    fusion = {
        "type": vision.get("class"),
        "encoder": vision.get("encoder") or vision.get("model_version"),
        "ocr_text": ocr_text[:400],
        "reuse": reused,
        "reuse_similarity_pct": reuse_pct,
        "reuse_hamming": reuse_hamming,
        "reuse_bits": bits,
        "animal_health_relevance": relevance,
    }
    return {
        "ok": True,
        "image_id": image_id,
        "content_id": content_id,
        "storage_key": path,
        "sha256": fetched["sha256"],
        "phash": phash,
        "mime_type": fetched.get("mime_type"),
        "width": vision.get("width"),
        "height": vision.get("height"),
        "ocr_text": ocr_text[:2000],
        "cnn_class": vision.get("class"),
        "cnn_confidence": vision.get("confidence"),
        "reused": reused,
        "reuse_hamming": reuse_hamming,
        "reuse_similarity_pct": reuse_pct,
        "alt_text": alt_text,
        "source_url": url,
        "synthetic": False,
        "model_versions": {
            "cnn": vision.get("model_version"),
            "encoder": vision.get("encoder"),
            "role": vision.get("role"),
            "ocr": ocr.get("model_version"),
            "hash": hashed.get("model_version"),
            "visual_fusion": fusion,
            "academic": vision.get("academic"),
        },
        "cnn": vision,
        "ocr": ocr,
        "ocr_engine": ocr.get("engine") or ocr.get("model_version"),
        "visual_fusion": fusion,
    }


def write_class_png(path: Path, label: str, seed: int = 0) -> Path:
    """Imagen sintética reconocible por clase (para corpus sin foto de artículo)."""
    try:
        from cnn import IMAGE_CLASSES
        from train_cnn import _make_image
        import random

        chosen = label if label in IMAGE_CLASSES else "PHOTOGRAPH"
        img = _make_image(chosen, seed, random.Random(seed))
        path.parent.mkdir(parents=True, exist_ok=True)
        img.resize((256, 256)).save(path)
        return path
    except Exception:
        return write_placeholder_png(path)


def write_placeholder_png(path: Path, color: tuple[int, int, int] = (32, 96, 64)) -> Path:
    """PNG mínimo para demo/tests si no hay red."""
    try:
        from PIL import Image

        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 64), color).save(path)
        return path
    except Exception:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
            b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return path
