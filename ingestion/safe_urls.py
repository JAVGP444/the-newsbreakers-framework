"""URLs públicas: solo http(s) a dominios oficiales/confiables.

Los artículos de rumor o redes sin fuente real se guardan con URL vacía
o token `inapp:` y se abren solo dentro del dashboard (`#/article/{id}`).
"""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_SUFFIXES = (
    "woah.org",
    "oie.int",
    "fao.org",
    "who.int",
    "paho.org",
    "gob.mx",
    "cdc.gov",
    "usda.gov",
    "nih.gov",
    "un.org",
    "europa.eu",
    "youtube.com",
    "youtu.be",
    "openalex.org",
    "pubmed.ncbi.nlm.nih.gov",
    "openstreetmap.org",
    "senasica.gob.mx",
    "who.int",
    "wahis.woah.org",
)

BLOCKED_HOSTS = {
    "example.invalid",
    "example.com",
    "example.org",
    "www.example.com",
    "www.example.org",
    "www.example.invalid",
    "social.local",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

FAKE_NEEDLES = (
    "example.invalid",
    "example.com",
    "social.local",
    "rumor-vacuna",
    "rumor vacuna",
)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def is_fake_url(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    if any(n in lower for n in FAKE_NEEDLES):
        return True
    host = _host(raw)
    if host in BLOCKED_HOSTS:
        return True
    if host.endswith(".example.com") or host.endswith(".example.invalid"):
        return True
    if lower.startswith(("inapp:", "catalog://", "file:")):
        return False
    return False


def host_allowed(host: str) -> bool:
    host = (host or "").lower().rstrip(".")
    if not host or host in BLOCKED_HOSTS:
        return False
    for suffix in ALLOWED_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def is_allowlisted_http(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw or is_fake_url(raw):
        return False
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    return host_allowed(parsed.hostname or "")


def public_http_url(url: str | None) -> str:
    """URL segura para persistir/mostrar, o cadena vacía (navegación in-app)."""
    raw = (url or "").strip()
    if not raw or is_fake_url(raw):
        return ""
    if is_allowlisted_http(raw):
        return raw
    return ""


def stored_article_url(url: str | None, content_id: str = "") -> str:
    """Persiste http(s) reales; vacía example.invalid / localhost / hosts bloqueados."""
    raw = (url or "").strip()
    if not raw or is_fake_url(raw):
        return ""
    if raw.startswith("inapp:"):
        return raw
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in BLOCKED_HOSTS:
        return ""
    if host.endswith(".example.com") or host.endswith(".example.invalid"):
        return ""
    return raw
