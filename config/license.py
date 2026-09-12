"""Licencia de pago.

Gratis: ver Sala, CNN, gráficos, traductor, y un ciclo corto (8 fuentes).
Se paga: minería 24/7 de toda la watchlist, GDELT/RSS completos, OpenAI/Anthropic y OCR Studio.

Formato: TNB1.<payload_b64url>.<hmac8hex>
Payload JSON: {"who":"...","exp":"2027-12-31","f":["mine","llm","ocr"]}
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from config.paths import app_home

ROOT = app_home()
FEATURES = ("mine", "llm", "ocr")
PREVIEW_N = 4
COMMUNITY_CAPS = {
    "max_sources": 8,
    "gdelt_max": 12,
    "gdelt_windows": 1,
    "rss_pages": 1,
    "rss_limit": 25,
    "html_listing_sources": 2,
}
# Firma local. Quien lea el código puede fabricar claves; para ventas serias
# cambia este pepper y vuelve a emitir.
PEPPER = "baa1d668852ea8a80d81d6768a4bb47bb4feda8b7fefb71a0bb31615b028540f"
_KEY_RE = re.compile(r"TNB1\.[A-Za-z0-9_-]+\.[0-9a-fA-F]{8,64}")


def normalize_key(text: str | None) -> str:
    raw = (text or "").replace("\u200b", "").strip().strip("`\"'")
    compact = re.sub(r"\s+", "", raw)
    found = _KEY_RE.search(compact) or _KEY_RE.search(raw)
    if found:
        return found.group(0)
    return compact


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def sign_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hmac.new(PEPPER.encode("ascii"), body, hashlib.sha256).hexdigest()[:16]
    return f"TNB1.{_b64url(body)}.{digest}"


def issue(who: str, days: int = 365, features: list[str] | None = None) -> str:
    feats = [f for f in (features or list(FEATURES)) if f in FEATURES]
    if not feats:
        feats = list(FEATURES)
    exp = date.today().fromordinal(date.today().toordinal() + max(1, int(days)))
    return sign_payload({"who": (who or "cliente").strip(), "exp": exp.isoformat(), "f": feats})


def _read_key_file() -> str:
    for path in (ROOT / "license.key", ROOT / "data" / "license.key"):
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text.splitlines()[0].strip()
    return ""


def raw_key() -> str:
    return (os.environ.get("TNB_LICENSE_KEY") or "").strip() or _read_key_file()


def parse(key: str | None = None) -> dict[str, Any]:
    token = normalize_key(key if key is not None else raw_key())
    if not token:
        return {"ok": False, "tier": "community", "features": [], "reason": "sin_clave"}
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "TNB1":
        return {"ok": False, "tier": "community", "features": [], "reason": "formato"}
    try:
        body = _b64url_decode(parts[1])
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return {"ok": False, "tier": "community", "features": [], "reason": "payload"}
    expect = hmac.new(PEPPER.encode("ascii"), body, hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(expect, parts[2]):
        return {"ok": False, "tier": "community", "features": [], "reason": "firma"}
    exp_s = str(payload.get("exp") or "")
    try:
        exp = datetime.strptime(exp_s, "%Y-%m-%d").date()
    except ValueError:
        return {"ok": False, "tier": "community", "features": [], "reason": "fecha"}
    if exp < datetime.now(timezone.utc).date():
        return {
            "ok": False,
            "tier": "community",
            "features": [],
            "reason": "caducada",
            "who": payload.get("who"),
            "exp": exp_s,
        }
    feats = [f for f in payload.get("f") or [] if f in FEATURES]
    return {
        "ok": True,
        "tier": "licensed",
        "features": feats,
        "who": payload.get("who"),
        "exp": exp_s,
        "reason": "ok",
    }


def is_licensed() -> bool:
    return bool(parse().get("ok"))


def allows(feature: str) -> bool:
    return is_licensed()


def apply_cap(feature: str, value: int, community: int) -> int:
    if allows(feature):
        return value
    return min(int(value), int(community))


def save_key(key: str) -> dict[str, Any]:
    token = normalize_key(key)
    info = parse(token)
    if not info.get("ok"):
        return info
    dest = ROOT / "data" / "license.key"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(token + "\n", encoding="utf-8")
    os.environ["TNB_LICENSE_KEY"] = token
    return parse()


def public_status() -> dict[str, Any]:
    info = parse()
    licensed = bool(info.get("ok"))
    return {
        "ok": licensed,
        "tier": "licensed" if licensed else "preview",
        "preview": not licensed,
        "preview_n": PREVIEW_N,
        "features": list(FEATURES) if licensed else [],
        "who": info.get("who"),
        "exp": info.get("exp"),
        "reason": info.get("reason"),
        "free": [
            f"{PREVIEW_N} notas de muestra para ver el tipo de vigilancia",
        ],
        "paid": [
            "Sala completa, gráficos, mapa, grafo, CNN y revisión",
            "Minería 24/7 de toda la watchlist",
            "OpenAI/Anthropic en las fichas (tu API key)",
            "OCR Document Intelligence si tienes el Studio",
        ],
    }
