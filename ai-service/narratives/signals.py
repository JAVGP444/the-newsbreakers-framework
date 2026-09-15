"""Contraste de narrativas. Señales sí; sello de fake o malicia, no."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlparse

from lexicon import BANK, CATEGORY_LABEL, PRINCIPLE, STRUCTURES, term_weight

SENT_SPLIT = re.compile(r"(?<=[.!?¿])\s+|\n+")
WORD = re.compile(r"[a-záéíóúüñ]{3,}", re.I)
ATTR = re.compile(
    r"\b(acusa|acusan|según|afirman que|usuarios afirman|la oposición|algunos usuarios|se dice que)\b",
    re.I,
)
HYP = re.compile(r"\b(podría|podrian|tal vez|quizá|quiza|hipótesis|especula)\b", re.I)
DESC = re.compile(r"\b(analiza|investiga|estudio|investigación analiza)\b", re.I)
NEG = re.compile(
    r"\b(no existe evidencia|no hay evidencia|no se ocult|niega que|desmiente|no es cierto)\b",
    re.I,
)
MODALITY_LABEL = {
    "afirmacion": "Afirmación",
    "negacion": "Negación",
    "pregunta": "Pregunta",
    "hipotesis": "Hipótesis",
    "cita": "Cita / atribución",
    "descripcion": "Descripción",
    "opinion": "Opinión",
}

METHOD = [
    {
        "id": "objetivo",
        "title": "Qué hace y qué no",
        "text": (
            "The NewsBreakers no es un detector de fake news. Lee narrativas de salud animal, "
            "parte las afirmaciones, las cruza con fuentes y marca señales. "
            "No declara que una noticia sea maliciosa porque aparezca una palabra."
        ),
    },
    {
        "id": "flujo",
        "title": "Flujo",
        "text": (
            "Detectar señales → leer contexto y modalidad → extraer afirmaciones → "
            "contrastar evidencia → nivel de riesgo → priorizar revisión humana."
        ),
    },
    {
        "id": "banco",
        "title": "Banco de palabras",
        "text": (
            "Ocultar, mentira o pánico solo quieren decir: mira esta parte con más calma. "
            "No quieren decir: esta nota es falsa."
        ),
    },
    {
        "id": "contexto",
        "title": "La palabra no es el riesgo",
        "text": (
            "«Las autoridades ocultaron el brote» pide contraste. "
            "La misma frase en pregunta, en negación, puesta en boca de la oposición "
            "o descrita como objeto de una investigación no es la misma afirmación."
        ),
    },
    {
        "id": "contraste",
        "title": "Contraste",
        "text": (
            "Cada afirmación se mira contra fichas oficiales (OMS, WOAH, FAO, SENASICA, CDC, USDA), "
            "prensa, academia y otras notas. No todas las fuentes pesan igual. "
            "La ficha dice qué afirma la nota, qué prueba trae, qué dicen las autoridades, "
            "qué no coincide y qué sigue sin evidencia."
        ),
    },
    {
        "id": "grafo",
        "title": "Grafo y nube",
        "text": (
            "El grafo une conceptos que aparecen juntos. Fuerza 5 es relación frecuente, "
            "no malicia. La nube muestra vocabulario del recorte. Los filtros recortan por "
            "categoría, fuerza, país, enfermedad y fecha."
        ),
    },
    {
        "id": "clase",
        "title": "Clasificación",
        "text": (
            "Respaldada, parcialmente respaldada, no verificable, potencialmente engañosa, "
            "contradicha, prioridad de investigación. Esa última es cola humana, no una sentencia de intención."
        ),
    },
]


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn").lower()


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_SPLIT.split(text or "") if p and p.strip()]
    return parts or ([text.strip()] if (text or "").strip() else [])


def modality(sentence: str) -> str:
    s = (sentence or "").strip()
    if not s:
        return "afirmacion"
    if s.endswith("?") or s.startswith("¿") or s.lower().startswith(("¿", "qué ", "que ")):
        return "pregunta"
    if NEG.search(s):
        return "negacion"
    if ATTR.search(s):
        return "cita"
    if DESC.search(s):
        return "descripcion"
    if HYP.search(s):
        return "hipotesis"
    if s.lower().startswith(("creo que", "parece que", "en mi opinión")):
        return "opinion"
    return "afirmacion"


def _hits_in(folded: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for cat, terms in BANK.items():
        for term in sorted(terms, key=len, reverse=True):
            needle = _fold(term)
            if needle and needle in folded:
                key = (cat, term)
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    {
                        "category": cat,
                        "term": term,
                        "label": CATEGORY_LABEL.get(cat, cat),
                        "weight": term_weight(cat),
                    }
                )
    return found


def context_note(sentence: str, hits: list[dict[str, str]]) -> str:
    kind = modality(sentence)
    has_hide = any(h["category"] == "ocultamiento" for h in hits)
    if not has_hide:
        if kind == "pregunta":
            return "Es una pregunta, no una afirmación lista para contrastar como hecho."
        return PRINCIPLE
    if kind == "pregunta":
        return "Es una pregunta. No se trata como acusación."
    if kind == "negacion":
        return "La frase niega la acusación de ocultamiento."
    if kind == "cita":
        return "La acusación está atribuida a otro actor, no necesariamente al autor de la nota."
    if kind == "descripcion":
        return "Describe una investigación o un análisis; no afirma el ocultamiento por sí misma."
    if kind == "hipotesis":
        return "Está en modo hipótesis o especulación."
    return "Hay señal de ocultamiento en una afirmación. Hay que contrastar; no es un sello de falsedad."


def split_compound(sentence: str) -> list[str]:
    """Parte una frase larga en afirmaciones más chicas. No inventa hechos."""
    s = re.sub(r"\s+", " ", (sentence or "").strip())
    if len(s) < 40:
        return [s] if s else []
    chunks = re.split(r",\s+y\s+| y que | para (?=evitar|no |ocult)|\s+y\s+(?=las |los |el |la )", s, flags=re.I)
    out = []
    for chunk in chunks:
        piece = chunk.strip(" ,.;")
        if len(piece) >= 18:
            out.append(piece[0].upper() + piece[1:] if piece else piece)
    if len(out) <= 1:
        return [s]
    return out[:8]


def pair_force(count: int, same_sentence: int) -> int:
    if count >= 40:
        n = 5
    elif count >= 20:
        n = 4
    elif count >= 8:
        n = 3
    elif count >= 3:
        n = 2
    else:
        n = 1
    if same_sentence:
        n = min(5, n + 1)
    return n


def analyze_text(text: str) -> dict[str, Any]:
    sentences = split_sentences(text)
    signals: list[dict[str, Any]] = []
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_same: Counter[tuple[str, str]] = Counter()
    structures: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []

    for sent in sentences:
        folded = _fold(sent)
        hits = _hits_in(folded)
        kind = modality(sent)
        note = context_note(sent, hits)
        if hits:
            signals.append(
                {
                    "sentence": sent[:400],
                    "modality": kind,
                    "modality_label": MODALITY_LABEL[kind],
                    "hits": hits,
                    "note": note,
                    "not_a_verdict": True,
                }
            )
        cats = sorted({h["category"] for h in hits})
        for i, a in enumerate(cats):
            for b in cats[i + 1 :]:
                key = (a, b) if a < b else (b, a)
                pair_counts[key] += 1
                pair_same[key] += 1
        for spec in STRUCTURES:
            need = set(spec["need"])
            if not need.issubset(set(cats)):
                continue
            extra = spec.get("require_any") or ()
            if extra and not any(_fold(x) in folded for x in extra):
                continue
            structures.append(
                {
                    "id": spec["id"],
                    "label": spec["label"],
                    "sentence": sent[:280],
                    "modality": kind,
                    "note": "Estructura narrativa a contrastar. No es malicia automática.",
                }
            )
        if hits and kind == "afirmacion":
            for piece in split_compound(sent):
                claims.append(
                    {
                        "text": piece,
                        "modality": kind,
                        "parent": sent[:280],
                    }
                )

    pairs = []
    for (a, b), n in pair_counts.most_common(40):
        pairs.append(
            {
                "a": a,
                "b": b,
                "a_label": CATEGORY_LABEL.get(a, a),
                "b_label": CATEGORY_LABEL.get(b, b),
                "count": n,
                "force": pair_force(n, pair_same[(a, b)]),
                "relation": "coaparicion",
            }
        )
    cloud = Counter()
    for sig in signals:
        for h in sig["hits"]:
            cloud[h["term"]] += 1
    return {
        "principle": PRINCIPLE,
        "signals": signals[:30],
        "claims": claims[:12],
        "pairs": pairs,
        "structures": structures[:12],
        "cloud": [{"term": t, "count": c} for t, c in cloud.most_common(40)],
        "signal_count": len(signals),
        "structure_count": len(structures),
    }


def _nli_bucket(label: str | None) -> str:
    raw = (label or "").lower()
    if "contrad" in raw:
        return "contradicha"
    if "support" in raw or "respald" in raw:
        return "respaldada"
    if "engañ" in raw or "misleading" in raw:
        return "potencialmente_engañosa"
    if "revis" in raw or "hitl" in raw:
        return "prioridad_investigacion"
    return "no_verificable"


def classify_narrative(text_pack: dict[str, Any], claims: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Capa de narrativas. Nunca pone «maliciosa» como sentencia."""
    claims = claims or []
    labels = [_nli_bucket(c.get("nli_label") or c.get("verdict")) for c in claims]
    structs = text_pack.get("structure_count") or 0
    hide_afirm = any(
        s.get("modality") == "afirmacion"
        and any(h.get("category") == "ocultamiento" for h in s.get("hits") or [])
        for s in text_pack.get("signals") or []
    )
    if "contradicha" in labels and labels.count("contradicha") >= max(1, len(labels) // 2):
        code, label = "contradicha", "Contradicha"
        why = "La evidencia oficial choca con la afirmación principal."
    elif "respaldada" in labels and "contradicha" not in labels and structs == 0:
        if len(set(labels)) > 1:
            code, label = "parcial", "Parcialmente respaldada"
            why = "Una parte encaja con las fichas; otra sigue abierta."
        else:
            code, label = "respaldada", "Respaldada"
            why = "Las fichas alinean con la afirmación."
    elif hide_afirm and structs >= 1 and "respaldada" not in labels:
        code, label = "prioridad_investigacion", "Prioridad de investigación"
        why = (
            "Hay acusación de ocultamiento en modo afirmación y una estructura de relato. "
            "Cola humana; no es una sentencia de intención maliciosa."
        )
    elif "potencialmente_engañosa" in labels:
        code, label = "potencialmente_engañosa", "Potencialmente engañosa"
        why = "Puede inducir una lectura incorrecta. Hay que revisar omisiones y contexto."
    else:
        code, label = "no_verificable", "No verificable"
        why = "No hay evidencia bastante para confirmar ni descartar."
    return {
        "code": code,
        "label": label,
        "why": why,
        "not_malicious_verdict": True,
        "human_priority": code == "prioridad_investigacion",
    }


def contrast_card(
    article: dict[str, Any],
    claims: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    pack: dict[str, Any],
) -> dict[str, Any]:
    main = (pack.get("claims") or claims or [{}])
    main_text = (main[0].get("text") if main else None) or article.get("title") or ""
    evid_txt = []
    official = []
    for ev in evidence[:8]:
        host = ""
        try:
            host = urlparse(ev.get("url") or "").hostname or ""
        except Exception:
            host = ""
        row = {"title": ev.get("title") or host, "url": ev.get("url"), "host": host}
        evid_txt.append(row)
        if any(k in host for k in ("woah.org", "who.int", "fao.org", "gob.mx", "cdc.gov", "usda.gov", "aphis")):
            official.append(row)
    nli = [c.get("nli_label") for c in claims if c.get("nli_label")]
    contrad = [c for c in claims if str(c.get("nli_label") or "").lower().find("contrad") >= 0]
    unknown = [c for c in claims if str(c.get("nli_label") or "").lower() in {"", "unknown", "sin verificar", "insuficiente"}]
    blob = f"{article.get('title') or ''} {article.get('text') or ''}".lower()
    legal_needed = "oblig" in blob or "plazo" in blob
    return {
        "afirmacion": main_text[:500],
        "evidencia_afirmacion": "La nota aporta título y cuerpo; no se toma como prueba de sí misma.",
        "evidencia_externa": evid_txt,
        "informacion_oficial": official,
        "contexto": pack.get("signals")[:3] if pack.get("signals") else [],
        "contradicciones": [
            {"text": c.get("text"), "nli": c.get("nli_label")} for c in contrad[:5]
        ],
        "no_comprobado": [
            {"text": c.get("text"), "nli": c.get("nli_label")} for c in unknown[:5]
        ],
        "normativa": (
            "La nota habla de obligación de reportar. Hay que contrastar plazos y autoridad "
            "(WOAH / SENASICA). El módulo no cita un artículo legal automático."
            if legal_needed
            else None
        ),
        "conclusion": classify_narrative(pack, claims),
        "nli_seen": nli[:8],
    }


OFFICIAL_HOSTS = (
    "woah.org",
    "who.int",
    "fao.org",
    "cdc.gov",
    "gob.mx",
    "usda.gov",
    "aphis.usda.gov",
    "paho.org",
)


def analyze_article(
    article: dict[str, Any],
    claims: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = f"{article.get('title') or ''}. {article.get('text') or ''}"
    pack = analyze_text(text)
    claims = claims or []
    evidence = evidence or []
    pack["contrast"] = contrast_card(article, claims, evidence, pack)
    pack["classification"] = pack["contrast"]["conclusion"]
    pack["origin"] = {
        "country": article.get("country"),
        "language": article.get("language"),
        "source_id": article.get("source_id"),
        "published_at": article.get("published_at"),
        "url": article.get("url"),
    }
    return pack


def corpus_pack(articles: list[dict[str, Any]], *, force_min: int = 1) -> dict[str, Any]:
    cloud: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_same: Counter[tuple[str, str]] = Counter()
    cat_cloud: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    nodes: dict[str, dict[str, Any]] = {}
    sample = 0
    for row in articles:
        sample += 1
        pack = analyze_text(f"{row.get('title') or ''} {row.get('text') or ''}")
        for item in pack.get("cloud") or []:
            cloud[item["term"]] += int(item["count"] or 0)
        for p in pack.get("pairs") or []:
            key = (p["a"], p["b"])
            pair_counts[key] += int(p["count"] or 0)
            if int(p.get("force") or 0) >= 3:
                pair_same[key] += 1
        for s in pack.get("signals") or []:
            for h in s.get("hits") or []:
                cat_cloud[h["category"]] += 1
                nid = h["category"]
                if nid not in nodes:
                    nodes[nid] = {
                        "id": nid,
                        "label": h["label"],
                        "group": "narrative",
                        "value": 0,
                        "filter": {"q": h["term"]},
                    }
                nodes[nid]["value"] = int(nodes[nid]["value"]) + 1
        for st in pack.get("structures") or []:
            structures[st["label"]] += 1
    pairs = []
    edges = []
    seen = set()
    for (a, b), n in pair_counts.most_common(60):
        force = pair_force(n, pair_same[(a, b)])
        if force < force_min:
            continue
        pairs.append(
            {
                "a": a,
                "b": b,
                "a_label": CATEGORY_LABEL.get(a, a),
                "b_label": CATEGORY_LABEL.get(b, b),
                "count": n,
                "force": force,
                "relation": "narrativa",
            }
        )
        key = (a, b)
        if key not in seen and a in nodes and b in nodes:
            seen.add(key)
            edges.append({"from": a, "to": b, "label": str(force)})
    return {
        "principle": PRINCIPLE,
        "method": METHOD,
        "sample": sample,
        "cloud": [{"term": t, "count": c} for t, c in cloud.most_common(48)],
        "categories": [
            {"id": k, "label": CATEGORY_LABEL.get(k, k), "count": n, "weight": term_weight(k)}
            for k, n in cat_cloud.most_common()
        ],
        "pairs": pairs,
        "structures": [{"label": k, "count": n} for k, n in structures.most_common()],
        "graph": {"nodes": list(nodes.values()), "edges": edges, "empty": not edges},
        "bank": {
            k: {"label": CATEGORY_LABEL.get(k, k), "terms": list(v), "weight": term_weight(k)}
            for k, v in BANK.items()
        },
    }


def evidence_use_by_host(evidence_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for ev in evidence_rows:
        try:
            host = (urlparse(ev.get("url") or "").hostname or "").lower().removeprefix("www.")
        except Exception:
            continue
        if not host:
            continue
        counts[host] += 1
    return dict(counts)
