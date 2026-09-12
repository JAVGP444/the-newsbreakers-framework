"""Filtros canónicos del observatorio (querystring ↔ SQL/Python)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


VERDICT_ALIASES = {
    "respaldado": ("respald", "supported"),
    "insuficiente": ("insufic",),
    "contradicho": ("contrad",),
    "engañoso": ("engañ", "engan", "mislead"),
    "revision_humana": ("humana", "revision", "review"),
    "sin_verificar": ("unknown", "sin verificar", "sin_verificar"),
}

ORIGIN_ORDER = ("oficial", "cientifico", "social", "youtube", "prensa")
ORIGIN_LABELS = {
    "oficial": "Oficial",
    "cientifico": "Científico",
    "social": "Redes",
    "youtube": "YouTube",
    "prensa": "Prensa",
}
VERDICT_CHART_ORDER = (
    ("respaldado", "Respaldado"),
    ("insuficiente", "Insuficiente"),
    ("contradicho", "Contradicho"),
    ("revision_humana", "Revisión humana"),
)
VERDICT_CHART_LABELS = {
    **dict(VERDICT_CHART_ORDER),
    "enganoso": "Posiblemente engañoso",
    "sin_verificar": "Sin verificar",
}


@dataclass
class ArticleQuery:
    disease: str | None = None
    compare: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    country: str | None = None
    verdict: str | None = None
    source_id: str | None = None
    q: str | None = None
    origin: str | None = None
    raw_format: str | None = None
    stance: str | None = None
    risk_min: int | None = None
    risk_max: int | None = None
    risk_null: bool = False
    page: int = 1
    page_size: int = 12
    order: str = "published_at"

    def as_filter_dict(self) -> dict[str, Any]:
        return {
            "disease": self.disease,
            "compare": ",".join(self.compare) if self.compare else None,
            "from": self.date_from,
            "to": self.date_to,
            "country": self.country,
            "verdict": self.verdict,
            "source": self.source_id,
            "q": self.q,
            "origin": self.origin,
            "raw_format": self.raw_format,
            "stance": self.stance,
        }


def _clean(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _origin_id(value: str | None) -> str | None:
    key = (_clean(value) or "").lower().replace(" ", "_")
    if key in {"redes", "red"}:
        return "social"
    if key in ORIGIN_LABELS:
        return key
    return None


def content_origin(row: dict[str, Any]) -> str:
    url = str(row.get("url") or "").lower()
    type_blob = f"{row.get('source_type') or ''} {row.get('raw_format') or ''}".lower()
    title = f"{row.get('title') or ''} {row.get('text') or ''}".lower()
    if "youtube" in url or "youtu.be" in url or "youtube" in type_blob:
        return "youtube"
    if (
        any(host in url for host in ("openalex.org", "pubmed", "doi.org"))
        or "pubmed" in title
        or "openalex" in title
        or "cientif" in type_blob
        or "investig" in type_blob
    ):
        return "cientifico"
    if (
        any(host in url for host in ("woah.org", "oie.int", "senasica", "gob.mx", "fao.org", "who.int", "cdc.gov", "usda.gov"))
        or "senasica" in title
        or "official portal" in title
        or "oficial" in type_blob
    ):
        return "oficial"
    if (
        any(host in url for host in ("twitter.com", "x.com", "facebook.com", "linkedin.com", "reddit.com"))
        or any(tag in type_blob for tag in ("social", "twitter", "linkedin", "facebook"))
    ):
        return "social"
    return "prensa"


def verdict_chart_key(value: str | None) -> str:
    blob = (value or "").strip().lower()
    if "respald" in blob or blob == "supported":
        return "respaldado"
    if "insufic" in blob:
        return "insuficiente"
    if "contrad" in blob:
        return "contradicho"
    if any(tag in blob for tag in ("humana", "revision", "review")):
        return "revision_humana"
    if any(tag in blob for tag in ("engañ", "engan", "mislead")):
        return "enganoso"
    return "sin_verificar"


def _date(value: str | None) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return article_day({"published_at": text}) or None


def _ints(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def parse_compare(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        key = part.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def normalize_source_id(raw: str | None) -> str | None:
    text = _clean(raw)
    if not text:
        return None
    if text.upper().startswith("SRC-") and not text.upper().startswith("SRC-SRC"):
        rest = text[4:]
        if rest.upper().startswith("SRC"):
            return rest
        return text
    return text


def parse_article_query(
    *,
    disease: str | None = None,
    compare: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    country: str | None = None,
    verdict: str | None = None,
    source: str | None = None,
    source_id: str | None = None,
    q: str | None = None,
    origin: str | None = None,
    raw_format: str | None = None,
    stance: str | None = None,
    risk_min: Any = None,
    risk_max: Any = None,
    risk_null: Any = False,
    page: Any = 1,
    page_size: Any = 12,
    limit: Any = None,
    order: str | None = None,
) -> ArticleQuery:
    size = _ints(page_size) or _ints(limit) or 12
    size = max(1, min(size, 400))
    page_n = max(1, _ints(page) or 1)
    return ArticleQuery(
        disease=_clean(disease),
        compare=parse_compare(compare),
        date_from=_date(date_from),
        date_to=_date(date_to),
        country=_clean(country),
        verdict=_clean(verdict),
        source_id=normalize_source_id(source or source_id),
        q=_clean(q),
        origin=_origin_id(origin),
        raw_format=_clean(raw_format),
        stance=_clean(stance),
        risk_min=_ints(risk_min),
        risk_max=_ints(risk_max),
        risk_null=_bool(risk_null),
        page=page_n,
        page_size=size,
        order=(order or "published_at").strip() or "published_at",
    )


def parse_article_datetime(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text or text.lower() in {"none", "null", "undefined"}:
        return None

    def _utc(dt: datetime) -> datetime:
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    if len(text) >= 8 and text[:8].isdigit() and (len(text) == 8 or text[8] == "T"):
        try:
            return datetime(int(text[:4]), int(text[4:6]), int(text[6:8]))
        except ValueError:
            pass
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return _utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            try:
                return datetime.fromisoformat(text[:19])
            except ValueError:
                pass
    try:
        dt = parsedate_to_datetime(text)
        if dt:
            return _utc(dt)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return _utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def article_day(row: dict[str, Any]) -> str:
    dt = parse_article_datetime(row.get("published_at")) or parse_article_datetime(row.get("collected_at"))
    return dt.date().isoformat() if dt else ""


def published_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    """Orden DESC: primero las que tienen fecha de publicación, luego las demás."""
    pub = parse_article_datetime(row.get("published_at"))
    if pub:
        return (1, pub.isoformat())
    col = parse_article_datetime(row.get("collected_at"))
    return (0, col.isoformat() if col else "")


def verdict_matches(value: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    blob = (value or "").lower()
    key = needle.strip().lower()
    if key in blob or blob in key:
        return True
    aliases = VERDICT_ALIASES.get(key.replace(" ", "_"))
    if aliases and any(a in blob for a in aliases):
        return True
    return False


def stance_matches(value: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    blob = (value or "Unknown").lower()
    key = needle.strip().lower()
    if key in {"supported", "respaldado"}:
        return "support" in blob or "respald" in blob
    if key in {"contradicted", "contradicho"}:
        return "contrad" in blob
    if key in {"unknown", "sin_verificar", "sin verificar"}:
        return "unknown" in blob or blob in {"", "sin verificar"}
    return key in blob


def origin_matches(row: dict[str, Any], needle: str | None) -> bool:
    wanted = _origin_id(needle)
    if not wanted:
        return True
    return content_origin(row) == wanted
