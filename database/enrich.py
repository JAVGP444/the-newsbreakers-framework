"""Rellena fichas incompletas (título sin cuerpo, entidades, evidencia, imagen).

Se ejecuta al ingestar y, si faltan campos, en GET /articles/{id}.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_FW = Path(__file__).resolve().parents[1]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))

from bootstrap import IMAGES_DIR, ensure_paths  # noqa: E402

ensure_paths()

from database.geo import country_info, resolve_article_country  # noqa: E402

DISEASE_ANIMAL = {
    "gripe_aviar": "aves",
    "gusano_barrenador": "bovino",
    "fiebre_porcina_clasica": "porcino",
}

DISEASE_ORGS = {
    "gripe_aviar": ("WOAH", "FAO", "SENASICA"),
    "gusano_barrenador": ("SENASICA", "WOAH", "USDA APHIS"),
    "fiebre_porcina_clasica": ("SENASICA", "WOAH", "FAO"),
}

DISEASE_KEYWORDS_ES = {
    "gripe_aviar": ("gripe aviar", "influenza aviar", "H5N1", "aves de corral", "HPAI"),
    "gusano_barrenador": ("gusano barrenador", "screwworm", "Cochliomyia", "miasis"),
    "fiebre_porcina_clasica": ("peste porcina clásica", "classical swine fever", "cerdos"),
}

DISEASE_COLORS = {
    "gripe_aviar": ("#1e3a5f", "#7dd3fc"),
    "gusano_barrenador": ("#14532d", "#86efac"),
    "fiebre_porcina_clasica": ("#4a1942", "#f0abfc"),
}

# URLs oficiales allowlisteadas, ligadas a la enfermedad (no el home genérico).
DISEASE_EVIDENCE: dict[str, list[dict[str, str]]] = {
    "gripe_aviar": [
        {
            "url": "https://www.woah.org/en/disease/avian-influenza/",
            "title": "WOAH — influenza aviar",
            "snippet": "Ficha oficial de WOAH/OMSA sobre influenza aviar (HPAI/LPAI): definición, especies susceptibles y notificación internacional.",
        },
        {
            "url": "https://www.cdc.gov/bird-flu/index.html",
            "title": "CDC — bird flu",
            "snippet": "CDC resume influenza aviar (bird flu), riesgo zoonótico y recomendaciones de salud pública.",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production",
            "snippet": "FAO Animal Production and Health: bioseguridad avícola y coordinación con servicios veterinarios.",
        },
        {
            "url": "https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza",
            "title": "USDA APHIS — avian influenza",
            "snippet": "APHIS vigila influenza aviar altamente patógena en aves de corral y aves silvestres.",
        },
    ],
    "gusano_barrenador": [
        {
            "url": "https://www.woah.org/en/disease/new-world-screwworm/",
            "title": "WOAH — gusano barrenador",
            "snippet": "Ficha WOAH del New World screwworm (Cochliomyia hominivorax): miasis obligatoria y control oficial.",
        },
        {
            "url": "https://www.aphis.usda.gov/livestock-poultry-disease/cattle/ticks/screwworm",
            "title": "USDA APHIS — screwworm",
            "snippet": "USDA/APHIS vigila el gusano barrenador del Nuevo Mundo y las restricciones de movimiento de ganado.",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production",
            "snippet": "FAO documenta miasis y sanidad de rumiantes en campañas regionales.",
        },
    ],
    "fiebre_porcina_clasica": [
        {
            "url": "https://www.woah.org/en/disease/classical-swine-fever/",
            "title": "WOAH — peste porcina clásica",
            "snippet": "Ficha WOAH de classical swine fever (PPC): virus, cerdos susceptibles y notificación.",
        },
        {
            "url": "https://www.fao.org/animal-production/en",
            "title": "FAO — animal production",
            "snippet": "FAO Animal Production and Health: prevención de peste porcina clásica.",
        },
    ],
}

GENERIC_EVIDENCE_URLS = {
    "https://www.woah.org/",
    "https://www.woah.org",
    "https://www.fao.org/",
    "https://www.fao.org",
    "https://www.fao.org/animal-health/en",
    "https://www.usda.gov/",
    "https://www.usda.gov",
    "https://www.gob.mx/senasica",
}

HINTS = (
    (("gripe aviar", "influenza aviar", "avian influenza", "bird flu", "h5n1", "h5n2", "hpai"), "gripe_aviar"),
    (("gusano barrenador", "screwworm", "cochliomyia", "myiasis", "miasis"), "gusano_barrenador"),
    (("peste porcina", "classical swine fever", "hog cholera", "csfv", "fiebre porcina"), "fiebre_porcina_clasica"),
)

# Title names a disease we do not catalog — do not paste avian/screwworm/PPC fichas.
OFF_CATALOG_TITLE = (
    "fiebre aftosa",
    "aftosa",
    "foot-and-mouth",
    "foot and mouth",
    "rabia",
    "brucelosis",
    "brucella",
    "tuberculosis bovina",
)

URL_PATH_DISEASE = (
    ("avian-influenza", "gripe_aviar"),
    ("bird-flu", "gripe_aviar"),
    ("avian/avian-influenza", "gripe_aviar"),
    ("screwworm", "gusano_barrenador"),
    ("new-world-screwworm", "gusano_barrenador"),
    ("classical-swine-fever", "fiebre_porcina_clasica"),
    ("peste-porcina-clasica", "fiebre_porcina_clasica"),
    ("foot-and-mouth", "fiebre_aftosa"),
)

EVIDENCE_LIMIT = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _xml(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _model_versions(article: dict[str, Any]) -> dict[str, Any]:
    raw = article.get("model_versions") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return dict(raw or {})


def _norm_evidence_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "/").rstrip("/") or "/"
    return f"{host}{path}"


def _evidence_host(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def evidence_url_diseases(url: str) -> set[str]:
    found: set[str] = set()
    key = _norm_evidence_url(url)
    blob = (url or "").lower()
    for did, items in DISEASE_EVIDENCE.items():
        for item in items:
            if _norm_evidence_url(item.get("url") or "") == key:
                found.add(did)
    for needle, did in URL_PATH_DISEASE:
        if needle in blob:
            found.add(did)
    return found


def diseases_for_official_evidence(article: dict[str, Any], store: Any) -> list[str]:
    """Solo enfermedades nombradas en título/URL o en el arranque del texto.

    No usa tags almacenados ni menciones tardías en artículos de historia/OPS.
    """
    title = (article.get("title") or "").lower()
    url = (article.get("url") or "").lower()
    head = f"{title} {url}"
    hits: list[str] = []
    for needles, did in HINTS:
        if any(n in head for n in needles):
            hits.append(did)
    if hits:
        return list(dict.fromkeys(hits))
    if any(n in title for n in OFF_CATALOG_TITLE):
        return []
    lead = (article.get("text") or "")[:400].lower()
    for needles, did in HINTS:
        if any(n in lead for n in needles):
            hits.append(did)
    return list(dict.fromkeys(hits))


def cap_official_cards(
    cards: list[dict[str, Any]],
    diseases: list[str] | None,
    *,
    limit: int = EVIDENCE_LIMIT,
) -> list[dict[str, Any]]:
    """Únicas por URL, 1 snippet por dominio, solo si la enfermedad coincide. Máx. 4."""
    allowed = {str(d) for d in (diseases or []) if d}
    seen_url: set[str] = set()
    seen_host: set[str] = set()
    out: list[dict[str, Any]] = []
    for card in cards:
        url = str(card.get("url") or "").strip()
        if not url:
            continue
        key = _norm_evidence_url(url)
        if key in seen_url:
            continue
        host = _evidence_host(url)
        if not host or host in seen_host:
            continue
        tagged = evidence_url_diseases(url)
        if tagged:
            if not allowed or not (tagged & allowed):
                continue
        else:
            continue
        seen_url.add(key)
        seen_host.add(host)
        out.append(card)
        if len(out) >= limit:
            break
    return out


def filter_article_evidence(
    article: dict[str, Any],
    evidence: list[dict[str, Any]],
    store: Any,
    *,
    limit: int = EVIDENCE_LIMIT,
) -> list[dict[str, Any]]:
    diseases = diseases_for_official_evidence(article, store)
    return cap_official_cards(evidence, diseases, limit=limit)


def infer_disease_ids(article: dict[str, Any], store: Any) -> list[str]:
    tags = list(store.article_diseases(article) or [])
    blob = f"{article.get('title') or ''} {article.get('text') or ''} {article.get('url') or ''}".lower()
    for needles, did in HINTS:
        if did in tags:
            continue
        if any(n in blob for n in needles):
            if did == "gripe_aviar" and any(x in blob for x in ("porcina", "swine fever", "hog cholera")):
                continue
            tags.append(did)
    return list(dict.fromkeys(tags))


def synthesize_text(article: dict[str, Any], source: dict[str, Any] | None, diseases: list[str], store: Any) -> str:
    title = (article.get("title") or "").strip() or "Documento sin título"
    src_name = (source or {}).get("name") or article.get("source_type") or article.get("source_id") or "fuente del observatorio"
    labels = [store.disease_label(d) for d in diseases] or ["salud animal"]
    kws: list[str] = []
    for did in diseases:
        kws.extend(DISEASE_KEYWORDS_ES.get(did, ()))
    if not kws:
        kws = [w for w in title.split() if len(w) > 3][:6]
    geo = country_info(resolve_article_country(article))
    country = geo.get("name") or "ámbito no determinado"
    return (
        f"«{title}» es un documento de {src_name} sobre {', '.join(labels)}. "
        f"No había cuerpo periodístico usable: el resumen se reconstruye con el título, "
        f"la fuente y palabras clave ({', '.join(kws[:6])}). "
        f"Ámbito geográfico: {country}."
    )


_ANIMAL_CANON = {
    "aviar": "aves",
    "ave": "aves",
    "aves": "aves",
    "aves de corral": "aves",
    "bovino": "bovino",
    "ganado": "bovino",
    "vacuno": "bovino",
    "porcino": "porcino",
    "cerdo": "porcino",
    "cerdos": "porcino",
}


def infer_entity_values(
    article: dict[str, Any],
    source: dict[str, Any] | None,
    diseases: list[str],
    store: Any,
) -> dict[str, list[str]]:
    from entities import extract_entities

    title = article.get("title") or ""
    url = article.get("url") or ""
    src_name = (source or {}).get("name") or ""
    # Solo título + URL + fuente: el texto sintético dispara falsos (usa en «usable», res en «resumen»).
    blob = f"{title} {url} {src_name}"
    grouped = {"DISEASE": [], "ANIMAL": [], "COUNTRY": [], "ORG": []}
    for ent in extract_entities(blob, diseases):
        kind = (ent.get("kind") or "").upper()
        if kind == "ORGANIZATION":
            kind = "ORG"
        if kind == "LOCATION":
            kind = "COUNTRY"
        if kind == "ANIMAL":
            continue
        if kind == "COUNTRY":
            continue
        value = str(ent.get("value") or "").strip()
        if kind in grouped and value:
            grouped[kind].append(value)

    blob = f"{title} {article.get('text') or ''}".lower()
    for did in diseases:
        label = store.disease_label(did)
        grouped["DISEASE"].append(label)
        animal = DISEASE_ANIMAL.get(did)
        if animal and animal.lower() in blob:
            grouped["ANIMAL"].append(animal)
        for org in DISEASE_ORGS.get(did, ()):
            if org.lower() in blob:
                grouped["ORG"].append(org)

    raw_code = (article.get("country") or "").strip().upper()
    if raw_code in {"", "XX"}:
        grouped["COUNTRY"].append(country_info(resolve_article_country(article, title) or "INT")["name"])
        if grouped["COUNTRY"][-1] == "Sin ubicar":
            grouped["COUNTRY"][-1] = "Internacional"
    else:
        grouped["COUNTRY"].append(country_info(raw_code)["name"])
    src_country = (source or {}).get("country")
    if src_country and str(src_country).upper() not in {"", raw_code}:
        extra = country_info(str(src_country).upper())
        if extra.get("name") and extra["name"] not in grouped["COUNTRY"]:
            grouped["COUNTRY"].append(extra["name"])

    host = ""
    try:
        host = (urlparse(article.get("url") or "").hostname or "").lower()
    except Exception:
        host = ""
    if "woah" in host or "oie" in host:
        grouped["ORG"].append("WOAH")
    if "fao" in host:
        grouped["ORG"].append("FAO")
    if "senasica" in host or "gob.mx" in host:
        grouped["ORG"].append("SENASICA")
    if "cdc.gov" in host:
        grouped["ORG"].append("CDC")
    if "usda" in host:
        grouped["ORG"].append("USDA")
    stype = f"{article.get('source_type') or ''} {article.get('raw_format') or ''}".lower()
    if "oficial" in stype:
        grouped["ORG"].append("SENASICA")

    if not grouped["ANIMAL"] and diseases:
        animal = DISEASE_ANIMAL.get(diseases[0])
        if animal and animal.lower() in blob:
            grouped["ANIMAL"].append(animal)
    if not grouped["ANIMAL"]:
        grouped["ANIMAL"].append("animal de producción")
    if not grouped["COUNTRY"]:
        grouped["COUNTRY"].append("Internacional")
    if not grouped["DISEASE"]:
        grouped["DISEASE"].append("salud animal")

    allowed_animals = {DISEASE_ANIMAL[d] for d in diseases if d in DISEASE_ANIMAL}
    cleaned: dict[str, list[str]] = {}
    for kind, values in grouped.items():
        seen: set[str] = set()
        out: list[str] = []
        for raw in values:
            value = store.disease_label(raw) if kind == "DISEASE" else raw
            if kind == "ANIMAL":
                value = _ANIMAL_CANON.get(value.lower(), value)
                if allowed_animals and value.lower() not in allowed_animals:
                    continue
            if kind == "COUNTRY" and len(value) <= 3 and value.isupper():
                value = country_info(value)["name"]
            key = value.lower().replace("_", " ")
            if key in seen or not value:
                continue
            seen.add(key)
            out.append(value)
        cleaned[kind] = out
    if not cleaned.get("ANIMAL"):
        cleaned["ANIMAL"] = list(allowed_animals) or ["animal de producción"]
    return cleaned


def build_lectura(
    article: dict[str, Any],
    entities: dict[str, list[str]],
    source: dict[str, Any] | None,
) -> str:
    title = (article.get("title") or "este documento").strip()
    verdict = (article.get("verdict") or "Sin verificar").strip()
    risk = article.get("risk_score")
    risk_txt = f"riesgo {risk}/100" if risk is not None else "riesgo no calculado"
    disease = ", ".join(entities.get("DISEASE") or []) or "salud animal"
    animal = ", ".join(entities.get("ANIMAL") or []) or "especie no precisada"
    country = ", ".join(entities.get("COUNTRY") or []) or "ámbito no determinado"
    orgs = ", ".join(entities.get("ORG") or []) or "WOAH, FAO"
    src = (source or {}).get("name") or article.get("source_type") or "el observatorio"
    return (
        f"Lectura del caso «{title}»: se clasifica como {verdict} con {risk_txt}. "
        f"Enfermedad: {disease}. Especie: {animal}. País o ámbito: {country}. "
        f"Organizaciones de referencia: {orgs}. Fuente: {src}. "
        f"El párrafo se arma con entidades, veredicto y riesgo; no decide si el contenido es verdadero."
    )


def disease_evidence_cards(diseases: list[str]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    for did in diseases or []:
        for item in DISEASE_EVIDENCE.get(did, []):
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            cards.append(item)
    return cap_official_cards(cards, diseases, limit=EVIDENCE_LIMIT)


def write_disease_svg(content_id: str, label: str, cnn_class: str, disease_id: str) -> Path:
    bg, fg = DISEASE_COLORS.get(disease_id, ("#0f2744", "#e2e8f0"))
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGES_DIR / f"ph_{content_id}.svg"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <rect width="960" height="540" fill="{bg}"/>
  <rect x="36" y="36" width="888" height="468" fill="none" stroke="{fg}" stroke-width="2" opacity="0.45"/>
  <text x="480" y="230" text-anchor="middle" fill="{fg}" font-family="Georgia, serif" font-size="42">{_xml(label)}</text>
  <text x="480" y="290" text-anchor="middle" fill="#cbd5e1" font-family="Segoe UI, sans-serif" font-size="20">{_xml(cnn_class)}</text>
  <text x="480" y="340" text-anchor="middle" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="16">Placeholder de enfermedad · observatorio</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def _persist_entities(store: Any, content_id: str, grouped: dict[str, list[str]]) -> None:
    store.execute(
        "DELETE FROM entities WHERE content_id=? AND kind IN ('ANIMAL','COUNTRY','LOCATION','ORG')",
        (content_id,),
    )
    existing = {
        (str(r.get("kind") or "").upper(), str(r.get("value") or "").strip().lower())
        for r in store.fetchall("SELECT kind, value FROM entities WHERE content_id=?", (content_id,))
    }
    for kind, values in grouped.items():
        for value in values:
            key = (kind, value.lower())
            if key in existing:
                continue
            eid = "ENT-" + hashlib.sha256(f"{content_id}:{kind}:{value}".encode()).hexdigest()[:16]
            store.insert_entity(
                {
                    "entity_id": eid,
                    "content_id": content_id,
                    "kind": kind,
                    "value": value,
                    "model_name": "ficha_enrich",
                    "model_version": "ficha_v1",
                }
            )
            existing.add(key)


def _ensure_claim(store: Any, article: dict[str, Any], diseases: list[str]) -> dict[str, Any]:
    content_id = article["content_id"]
    claims = store.list_claims(content_id)
    if claims:
        return claims[0]
    from claims import structure_claim

    text = (article.get("text") or article.get("title") or "salud animal").strip()
    claim = structure_claim(text[:240], "titulo", diseases)
    claim["content_id"] = content_id
    claim["nli_label"] = "Unknown"
    claim["verdict"] = article.get("verdict") or "Unknown"
    claim["confidence"] = 0.45
    claim["model_name"] = "ficha_enrich"
    claim["model_version"] = "ficha_v1"
    store.insert_claim(claim)
    return claim


def _replace_evidence(store: Any, claim_id: str, cards: list[dict[str, str]], claim_text: str = "") -> None:
    from nli import stance_from_text

    store.execute("DELETE FROM evidence WHERE claim_id=?", (claim_id,))
    for card in cards:
        url = card.get("url") or ""
        snippet = f"{card.get('title')}. {card.get('snippet')}"
        stance = stance_from_text(claim_text, snippet, url=url)
        eid = "EV-" + hashlib.sha256(f"{claim_id}:{url}".encode()).hexdigest()[:16]
        store.insert_evidence(
            {
                "evidence_id": eid,
                "claim_id": claim_id,
                "url": url,
                "source_tier": "official",
                "snippet": snippet,
                "stance": stance,
                "collected_at": _now(),
            }
        )


def _displayable_images(store: Any, content_id: str) -> list[dict[str, Any]]:
    out = []
    for im in store.list_images(content_id):
        key = str(im.get("storage_key") or "").replace("\\", "/")
        name = Path(key).name.lower()
        if name.startswith("ph_") or name.endswith(".svg"):
            continue
        if store.is_news_thumb(im):
            out.append(im)
    return out


def _ensure_image(store: Any, article: dict[str, Any], diseases: list[str]) -> None:
    from database.thumbs import ensure_article_thumb

    ensure_article_thumb(store, article)


def _needs_enrich(store: Any, article: dict[str, Any]) -> bool:
    content_id = article["content_id"]
    if _model_versions(article).get("enriched") != "ficha_v2":
        return True
    text = (article.get("text") or "").strip()
    title = (article.get("title") or "").strip()
    if not text or text == title or len(text) < 50:
        return True
    kinds = {str(r.get("kind") or "").upper() for r in store.fetchall("SELECT kind FROM entities WHERE content_id=?", (content_id,))}
    if "ANIMAL" not in kinds or "ORG" not in kinds:
        return True
    if "COUNTRY" not in kinds and "LOCATION" not in kinds:
        return True
    claims = store.list_claims(content_id)
    ev: list[dict[str, Any]] = []
    for claim in claims:
        ev.extend(store.list_evidence(claim["claim_id"]))
    expected = disease_evidence_cards(diseases_for_official_evidence(article, store))
    expected_urls = {_norm_evidence_url(c.get("url") or "") for c in expected}
    catalog_urls = {
        _norm_evidence_url(item.get("url") or "")
        for items in DISEASE_EVIDENCE.values()
        for item in items
    }
    stored_urls = {_norm_evidence_url(e.get("url") or "") for e in ev}
    if stored_urls & catalog_urls - expected_urls:
        return True
    if expected:
        matched = [e for e in ev if _norm_evidence_url(e.get("url") or "") in expected_urls]
        if len(matched) < min(2, len(expected)):
            return True
    thumb = str(article.get("thumb_path") or "").strip()
    from database.thumbs import thumb_path_for

    if not (thumb and Path(thumb).is_file()) and not thumb_path_for(content_id).is_file():
        if not _displayable_images(store, content_id):
            return True
    expl = (article.get("llm_explanation") or "").strip()
    if len(expl) < 80 or "solapamiento" in expl.lower():
        return True
    return False


def enrich_article(store: Any, content_id: str, *, force: bool = False) -> dict[str, Any]:
    """Completa texto, entidades, evidencia, imagen y lectura. Idempotente."""
    article = store.get_article(content_id)
    if not article:
        return {"ok": False, "reason": "missing"}
    if not force and not _needs_enrich(store, article):
        return {"ok": True, "skipped": True}

    source = store.get_source(article.get("source_id") or "") or {}
    diseases = infer_disease_ids(article, store)
    title = (article.get("title") or "").strip()
    text = (article.get("text") or "").strip()
    if not text or text == title or len(text) < 50:
        text = synthesize_text(article, source, diseases, store)
        article["text"] = text

    entities = infer_entity_values(article, source, diseases, store)
    _persist_entities(store, content_id, entities)

    claim = _ensure_claim(store, article, diseases)
    evidence_diseases = diseases_for_official_evidence(article, store)
    cards = disease_evidence_cards(evidence_diseases)
    try:
        from live_pages import live_evidence_cards

        live = live_evidence_cards(evidence_diseases, limit=EVIDENCE_LIMIT)
        if live:
            cards = live
    except Exception:
        pass
    cards = cap_official_cards(cards, evidence_diseases, limit=EVIDENCE_LIMIT)
    for other in store.list_claims(content_id):
        store.execute("DELETE FROM evidence WHERE claim_id=?", (other["claim_id"],))
    if cards:
        _replace_evidence(store, claim["claim_id"], cards, claim_text=claim.get("text") or article.get("title") or "")
    _ensure_image(store, article, diseases)

    lectura = build_lectura(article, entities, source)
    versions = _model_versions(article)
    versions["enriched"] = "ficha_v2"
    store.update_article_analysis(
        content_id,
        text=text,
        disease_tags=diseases,
        llm_explanation=lectura,
        llm_provider=article.get("llm_provider") or "local",
        model_versions=versions,
    )
    store.audit("article", content_id, "ficha_enrich", {"diseases": diseases, "entities": {k: v[:3] for k, v in entities.items()}})
    return {"ok": True, "skipped": False, "diseases": diseases, "entities": entities, "lectura": lectura}


def article_timeline(article: dict[str, Any]) -> list[dict[str, Any]]:
    published = (article.get("published_at") or article.get("collected_at") or "")[:19]
    analyzed = (article.get("collected_at") or published or _now())[:19]
    title = article.get("title") or article.get("content_id")
    verdict = article.get("verdict") or "Sin veredicto"
    risk = article.get("risk_score")
    risk_txt = f"Riesgo {risk}" if risk is not None else "Riesgo no calculado"
    events = [
        {"at": published or analyzed, "kind": "article", "label": "Publicado", "text": title},
        {
            "at": analyzed or published,
            "kind": "analysis",
            "label": "Analizado",
            "text": f"{verdict} · {risk_txt}",
        },
    ]
    return events


def similar_or_related(store: Any, content_id: str, limit: int = 5) -> list[dict[str, Any]]:
    rows = store.similar_articles(content_id, limit=limit)
    seen = {r["content_id"] for r in rows}
    if len(rows) >= limit:
        return rows[:limit]
    article = store.get_article(content_id) or {}
    tags = set(infer_disease_ids(article, store))
    for other in store.fetchall(
        "SELECT content_id, title, country, risk_score, disease_tags FROM articles WHERE content_id!=? ORDER BY collected_at DESC LIMIT 80",
        (content_id,),
    ):
        if other["content_id"] in seen:
            continue
        other_tags = set(store.article_diseases(other))
        if tags and not (tags & other_tags):
            continue
        rows.append(
            {
                "content_id": other["content_id"],
                "title": other.get("title") or other["content_id"],
                "score": 2 if tags & other_tags else 1,
                "reasons": ["misma enfermedad"] if tags & other_tags else ["mismo observatorio"],
                "country": other.get("country"),
                "risk_score": other.get("risk_score"),
            }
        )
        seen.add(other["content_id"])
        if len(rows) >= limit:
            break
    if len(rows) < limit:
        for other in store.fetchall(
            "SELECT content_id, title, country, risk_score FROM articles WHERE content_id!=? ORDER BY collected_at DESC LIMIT 20",
            (content_id,),
        ):
            if other["content_id"] in seen:
                continue
            rows.append(
                {
                    "content_id": other["content_id"],
                    "title": other.get("title") or other["content_id"],
                    "score": 1,
                    "reasons": ["reciente"],
                    "country": other.get("country"),
                    "risk_score": other.get("risk_score"),
                }
            )
            seen.add(other["content_id"])
            if len(rows) >= limit:
                break
    return rows[:limit]


def compact_graph(article: dict[str, Any], similar: list[dict[str, Any]], store: Any) -> dict[str, Any]:
    content_id = article["content_id"]
    nodes = [
        {
            "id": content_id,
            "label": (article.get("title") or "artículo")[:48],
            "group": "article",
            "value": 6,
        }
    ]
    edges = []
    for neigh in similar[:4]:
        nodes.append(
            {
                "id": neigh["content_id"],
                "label": (neigh.get("title") or neigh["content_id"])[:42],
                "group": "similar",
                "value": 2,
            }
        )
        edges.append({"from": content_id, "to": neigh["content_id"]})
    return {"nodes": nodes[:5], "edges": edges[:4]}
