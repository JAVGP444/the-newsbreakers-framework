"""Copia imágenes minadas al dataset CNN (models/cnn/dataset/{class}/).

Solo fotos reales descargadas (thumbs YouTube, imágenes de artículo)
con confianza >= 0.5. Nunca dibujos sintéticos ni corpus demo.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bootstrap import CNN_CLASSES, CNN_DATASET_DIR, ensure_paths

SKIP_NAME_BITS = (
    "fb_",
    "demo_seed_",
    "ph_",
    "corpus_",
    "casos",
    "cnn/dataset",
    "models/cnn",
    "cnn_synth",
    "inapp:",
)
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def cnn_min_confidence() -> float:
    try:
        return float(os.environ.get("TNB_CNN_DATASET_MIN_CONF") or 0.5)
    except ValueError:
        return 0.5


def assign_split(sha256: str) -> str:
    """Split determinista 70/15/15 a partir del hash."""
    try:
        n = int((sha256 or "0")[:8], 16) % 100
    except ValueError:
        n = 0
    if n < 70:
        return "train"
    if n < 85:
        return "val"
    return "test"


def _is_placeholder(path: Path, source_url: str = "", image_row: dict[str, Any] | None = None) -> bool:
    blob = f"{path.name} {path.as_posix()} {source_url}".replace("\\", "/").lower()
    if any(bit in blob for bit in SKIP_NAME_BITS):
        return True
    if (image_row or {}).get("synthetic"):
        return True
    src = (source_url or "").strip().lower()
    if src.startswith("inapp:") or src.startswith("data:"):
        return True
    if not (src.startswith("http://") or src.startswith("https://")):
        return True
    try:
        w = int((image_row or {}).get("width") or 0)
        h = int((image_row or {}).get("height") or 0)
        if w and h and w <= 64 and h <= 64:
            return True
    except (TypeError, ValueError):
        pass
    return False


def dataset_counts() -> dict[str, int]:
    ensure_paths()
    out: dict[str, int] = {}
    for label in CNN_CLASSES:
        folder = CNN_DATASET_DIR / label
        n = 0
        if folder.is_dir():
            n = sum(1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS)
        out[label] = n
    return out


def purge_synthetic_dataset() -> dict[str, int]:
    """Borra dibujos/demo del dataset si el nombre del archivo delata origen sintético."""
    ensure_paths()
    removed = 0
    for label in CNN_CLASSES:
        folder = CNN_DATASET_DIR / label
        if not folder.is_dir():
            continue
        for path in list(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in EXTS:
                continue
            name = path.name.lower()
            if any(bit in name for bit in ("fb_", "demo_seed_", "corpus_", "casos", "ph_")):
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    continue
            else:
                try:
                    from PIL import Image

                    with Image.open(path) as img:
                        w, h = img.size
                    if w <= 64 and h <= 64 and path.suffix.lower() == ".png":
                        path.unlink()
                        removed += 1
                except Exception:
                    continue
    return {"removed": removed, **dataset_counts()}


def maybe_export_cnn_sample(store: Any, image_row: dict[str, Any]) -> dict[str, Any] | None:
    """Copia a dataset/{class}/ si conf >= umbral. Idempotente por sha256."""
    ensure_paths()
    label = str(image_row.get("cnn_class") or "").strip()
    if label not in CNN_CLASSES:
        return None
    try:
        conf = float(image_row.get("cnn_confidence") or 0)
    except (TypeError, ValueError):
        return None
    if conf < cnn_min_confidence():
        return None
    sha = str(image_row.get("sha256") or "").strip()
    src = Path(str(image_row.get("storage_key") or ""))
    if not src.is_file():
        return None
    if _is_placeholder(src, str(image_row.get("source_url") or ""), image_row):
        return None
    if src.suffix.lower() not in EXTS:
        return None
    if sha and store.fetchone("SELECT 1 AS n FROM cnn_samples WHERE sha256=?", (sha,)):
        return None

    dest_dir = CNN_DATASET_DIR / label
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha or src.stem}{src.suffix.lower()}"
    if not dest.exists():
        try:
            shutil.copy2(src, dest)
        except OSError:
            return None

    split = assign_split(sha or hashlib.sha256(dest.name.encode()).hexdigest())
    sample_id = "CNN-" + hashlib.sha256(f"{label}:{dest.name}".encode()).hexdigest()[:16]
    row = {
        "sample_id": sample_id,
        "path": str(dest),
        "class": label,
        "split": split,
        "source_article_id": image_row.get("content_id"),
        "image_id": image_row.get("image_id"),
        "sha256": sha or None,
        "confidence": conf,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store.insert_cnn_sample(row)
    return row
