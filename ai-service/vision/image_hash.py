"""Hashes de imagen: SHA-256 + pHash DCT 16×16 (Hamming en bits).

Si no hay numpy/PIL, average-hash 8×8. Hamming se reporta también como %.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import SALIDA_DIR  # noqa: E402

MODEL_NAME = "imagehash_phash"
MODEL_VERSION = "phash16_dct_v1"
HASH_SIZE = 16


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def bit_length(hex_hash: str) -> int:
    return max(1, len(hex_hash or "") * 4)


def hamming(a: str, b: str) -> int:
    """Distancia de Hamming en bits (hex → bits)."""
    if not a or not b or len(a) != len(b):
        return bit_length(a or b or "0" * 16)
    dist = 0
    for c1, c2 in zip(a, b):
        try:
            dist += bin(int(c1, 16) ^ int(c2, 16)).count("1")
        except ValueError:
            dist += 4
    return dist


def similarity_pct(a: str, b: str) -> float:
    bits = bit_length(a if a and b and len(a) == len(b) else (a or b or "0"))
    if not a or not b or len(a) != len(b):
        return 0.0
    return round(100.0 * (1.0 - min(hamming(a, b), bits) / bits), 1)


def _dct_2d(matrix):
    import numpy as np

    def dct_1d(vec):
        n = vec.shape[0]
        out = np.zeros(n, dtype=np.float64)
        factor = np.pi / (2.0 * n)
        idx = np.arange(n)
        for k in range(n):
            out[k] = np.sum(vec * np.cos((2 * idx + 1) * k * factor))
        out[0] *= 1.0 / np.sqrt(2.0)
        return out * np.sqrt(2.0 / n)

    rows = np.stack([dct_1d(row) for row in matrix])
    return np.stack([dct_1d(col) for col in rows.T]).T


def _phash_pil(path: str, hash_size: int = HASH_SIZE) -> str:
    import numpy as np
    from PIL import Image

    img = Image.open(path).convert("L").resize((hash_size * 2, hash_size * 2), Image.Resampling.LANCZOS)
    pixels = np.asarray(img, dtype=np.float64)
    dct = _dct_2d(pixels)
    low = dct[:hash_size, :hash_size].copy()
    low[0, 0] = np.median(low)
    med = np.median(low)
    bits = (low > med).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bool(bit))
    width = hash_size * hash_size // 4
    return f"{value:0{width}x}"


def _ahash_pil(path: str, size: int = 8) -> str:
    from PIL import Image

    img = Image.open(path).convert("L").resize((size, size))
    pixels = [img.getpixel((x, y)) for y in range(size) for x in range(size)]
    avg = sum(pixels) / max(len(pixels), 1)
    bits = "".join("1" if p >= avg else "0" for p in pixels)
    return f"{int(bits, 2):0{size * size // 4}x}"


def _ahash_bytes(data: bytes, size: int = 8) -> str:
    if not data:
        return ""
    n = size * size
    step = max(1, len(data) // n)
    blocks = [data[i * step : (i + 1) * step] or b"\x00" for i in range(n)]
    means = [sum(block) / max(len(block), 1) for block in blocks]
    avg = sum(means) / n
    bits = "".join("1" if m >= avg else "0" for m in means)
    return f"{int(bits, 2):0{n // 4}x}"


def average_hash(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return ""
    try:
        return _phash_pil(str(file_path))
    except Exception:
        try:
            return _ahash_pil(str(file_path))
        except Exception:
            return _ahash_bytes(file_path.read_bytes())


def perceptual_hash(path: str) -> dict[str, Any]:
    file_path = Path(path)
    payload: dict[str, Any] = {
        "phash": "",
        "sha256": "",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "implemented": True,
        "bits": HASH_SIZE * HASH_SIZE,
        "note": "pHash DCT 16×16. Similitud = 100 × (1 − Hamming/bits).",
    }
    if file_path.is_file():
        payload["sha256"] = sha256_file(str(file_path))
        payload["phash"] = average_hash(str(file_path))
        payload["bits"] = bit_length(payload["phash"])
    return payload


def phash_stub(path: str) -> str:
    return str(perceptual_hash(path).get("phash") or "")


def hash_salida_captures(salida: Path | None = None) -> list[dict[str, Any]]:
    root = Path(salida or SALIDA_DIR)
    rows: list[dict[str, Any]] = []
    if not root.is_dir():
        return rows
    for path in sorted(root.iterdir()):
        if path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
            continue
        rows.append({"path": str(path), **perceptual_hash(str(path))})
    return rows
