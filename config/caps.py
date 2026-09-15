"""Tope de fuentes y ventanas de captura. apply_cap deja pasar el valor pedido."""
from __future__ import annotations

from typing import Any

FEATURES = ("mine", "llm", "ocr")
PIPE_LIMITS = {
    "max_sources": 8,
    "gdelt_max": 12,
    "gdelt_windows": 1,
    "rss_pages": 1,
    "rss_limit": 25,
    "html_listing_sources": 2,
}
COMMUNITY_CAPS = PIPE_LIMITS


def allows(_feature: str) -> bool:
    return True


def apply_cap(_feature: str, value: int, _limit: int) -> int:
    return int(value)


def public_status() -> dict[str, Any]:
    return {"ok": True, "tier": "open"}
