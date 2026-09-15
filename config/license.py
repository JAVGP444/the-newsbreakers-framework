"""Compatibilidad: no hay puerta de pago en este corte.

allows/apply_cap existen porque el pipeline los llama. Siempre dejan pasar.
"""
from __future__ import annotations

from typing import Any

FEATURES = ("mine", "llm", "ocr")
PREVIEW_N = 0
COMMUNITY_CAPS = {
    "max_sources": 8,
    "gdelt_max": 12,
    "gdelt_windows": 1,
    "rss_pages": 1,
    "rss_limit": 25,
    "html_listing_sources": 2,
}


def allows(_feature: str) -> bool:
    return True


def is_licensed() -> bool:
    return True


def apply_cap(_feature: str, value: int, _community: int) -> int:
    return int(value)


def public_status() -> dict[str, Any]:
    return {"ok": True, "tier": "open"}
