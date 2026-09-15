"""Hechos de una nota: enfermedad, lugar, animal, novedad.

El contraste útil compara ESTOS hechos con un boletín, no con la ficha de especie.
"""
from __future__ import annotations

import re
from typing import Any

from bootstrap import ensure_paths

ensure_paths()

from nli import DISEASE_ANCHORS, _tokens  # noqa: E402

PLACE_CANON: list[tuple[tuple[str, ...], str]] = [
    (("presidio",), "Presidio"),
    (("jeff davis", "jeffdavis"), "Jeff Davis"),
    (("texas",), "Texas"),
    (("nuevo méxico", "new mexico", "nuevo mexico"), "Nuevo México"),
    (("chiapas",), "Chiapas"),
    (("guanajuato",), "Guanajuato"),
    (("oaxaca",), "Oaxaca"),
    (("chihuahua",), "Chihuahua"),
    (("tamaulipas",), "Tamaulipas"),
    (("veracruz",), "Veracruz"),
    (("méxico", "mexico"), "México"),
    (("estados unidos", "united states", "ee.uu", "eeuu", "u.s.", "usa"), "EE.UU."),
]

ANIMAL_CANON: list[tuple[tuple[str, ...], str]] = [
    (("equine", "horse", "horses", "caballo", "caballos", "yegua"), "caballo"),
    (("calf", "calves", "bovine", "cattle", "ternero", "vaca", "vacuno", "bovino"), "bovino"),
    (("dog", "dogs", "perro", "perros"), "perro"),
    (("goat", "goats", "cabra"), "caprino"),
    (("sheep", "oveja", "ovino"), "ovino"),
    (("swine", "pig", "cerdo", "porcino"), "porcino"),
    (
        (
            "wildlife",
            "fauna",
            "silvestre",
            "lion",
            "leones",
            "monkey",
            "monos",
            "puma",
            "macaw",
            "pavo",
            "deer",
            "venado",
        ),
        "fauna silvestre",
    ),
    (("poultry", "aves", "chicken", "gallina"), "aves"),
]

DISEASE_CANON: list[tuple[tuple[str, ...], str]] = [
    (("screwworm", "barrenador", "cochliomyia", "hominivorax", "miasis", "gusano", "nws"), "gusano barrenador"),
    (("h5n1", "h5n2", "hpai", "influenza", "aviar", "avian", "gripe"), "gripe aviar"),
    (("porcina", "swine", "csfv", "hog cholera"), "peste porcina"),
]

NOVELTY_NEEDLES = ("first", "primer", "primera", "1st", "century", "siglo", "este siglo")


def _has_any(blob: str, needles: tuple[str, ...]) -> bool:
    for needle in needles:
        if " " in needle or "." in needle:
            if needle in blob:
                return True
        elif re.search(rf"\b{re.escape(needle)}\b", blob):
            return True
    return False


def extract_facts(text: str) -> dict[str, Any]:
    blob = re.sub(r"\s+", " ", (text or "").lower())
    places = [label for needles, label in PLACE_CANON if _has_any(blob, needles)]
    animals = [label for needles, label in ANIMAL_CANON if _has_any(blob, needles)]
    diseases = [label for needles, label in DISEASE_CANON if _has_any(blob, needles)]
    # Prefer the most specific place (listed first).
    places = list(dict.fromkeys(places))
    animals = list(dict.fromkeys(animals))
    diseases = list(dict.fromkeys(diseases))
    novelty = any(n in blob for n in NOVELTY_NEEDLES)
    return {
        "diseases": diseases,
        "places": places,
        "animals": animals,
        "novelty": novelty,
        "labels": _labels(diseases, places, animals, novelty),
    }


def _labels(diseases: list[str], places: list[str], animals: list[str], novelty: bool) -> list[str]:
    out = list(diseases) + places[:3] + animals[:2]
    if novelty:
        out.append("primer caso")
    return out


NAV_NOISE = (
    "vehcs",
    "pet travel",
    "take a pet",
    "bring a pet",
    "all submissions must",
    "accredited veterinarians",
    "javascript",
    "enable cookies",
)


def _usable_window(text: str) -> bool:
    low = (text or "").lower()
    if any(n in low for n in NAV_NOISE):
        return False
    if "latest news" in low[:50]:
        return False
    return True


def pick_paragraph(claim_text: str, body: str, min_chars: int = 40) -> tuple[str, int]:
    """Ventana de 1–2 frases con más hechos en común con la nota."""
    claim_facts = extract_facts(claim_text)
    text = re.sub(r"\s+", " ", body or "").strip()
    if len(text) < min_chars:
        return "", 0
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if len(p.strip()) >= 40 and _usable_window(p)]
    if not parts:
        return "", 0
    best = ""
    best_score = 0
    for i, part in enumerate(parts):
        nxt = parts[i + 1] if i + 1 < len(parts) and _usable_window(parts[i + 1]) else ""
        window = f"{part} {nxt}".strip() if nxt else part
        if not _usable_window(window):
            continue
        got = extract_facts(window)
        score = 0
        score += 2 * len(set(got["diseases"]) & set(claim_facts["diseases"]))
        score += 3 * len(set(got["places"]) & set(claim_facts["places"]))
        score += 3 * len(set(got["animals"]) & set(claim_facts["animals"]))
        if claim_facts["novelty"] and got["novelty"]:
            score += 2
        specific = (_tokens(window) & _tokens(claim_text)) - DISEASE_ANCHORS
        if len(specific) < 2 and score < 3:
            continue
        if score > best_score:
            best_score = score
            best = window[:700]
    return best, best_score


def compare_facts(claim_text: str, snippet: str) -> dict[str, Any]:
    claim = extract_facts(claim_text)
    got = extract_facts(snippet)
    shared_d = set(claim["diseases"]) & set(got["diseases"])
    shared_p = set(claim["places"]) & set(got["places"])
    shared_a = set(claim["animals"]) & set(got["animals"])
    missing_p = [p for p in claim["places"] if p not in got["places"]]
    missing_a = [a for a in claim["animals"] if a not in got["animals"]]
    extra_a = [a for a in got["animals"] if a not in claim["animals"]]

    if not shared_d:
        return {
            "status": "none",
            "stance": None,
            "why": "El fragmento no habla de la misma enfermedad.",
            "shared_places": sorted(shared_p),
            "shared_animals": sorted(shared_a),
        }

    core = bool(shared_p or shared_a)
    full = bool(claim["diseases"]) and (not claim["places"] or shared_p) and (not claim["animals"] or shared_a)
    if full and (shared_p or shared_a or (claim["novelty"] and got["novelty"])):
        why = "El boletín oficial afirma los mismos hechos (enfermedad"
        if shared_p:
            why += ", lugar"
        if shared_a:
            why += ", animal"
        why += ")."
        return {"status": "hit", "stance": "Supported", "why": why, "shared_places": sorted(shared_p), "shared_animals": sorted(shared_a)}

    if core:
        bits = ["Coincide en la enfermedad"]
        if shared_p:
            bits.append("y en " + ", ".join(sorted(shared_p)))
        if missing_a:
            bits.append("no menciona " + ", ".join(missing_a))
        elif extra_a:
            bits.append("habla de " + ", ".join(extra_a) + ", no de lo que dice la nota")
        if missing_p:
            bits.append("no sitúa el hecho en " + ", ".join(missing_p[:2]))
        return {
            "status": "partial",
            "stance": None,
            "why": "; ".join(bits) + ".",
            "shared_places": sorted(shared_p),
            "shared_animals": sorted(shared_a),
        }

    return {
        "status": "none",
        "stance": None,
        "why": "Nombra la enfermedad, pero no el lugar ni el animal de esta nota.",
        "shared_places": [],
        "shared_animals": [],
    }


def source_is_official(source: dict[str, Any] | None, url: str = "") -> bool:
    from nli import is_official_source

    if is_official_source(url or ""):
        return True
    if not source:
        return False
    blob = f"{source.get('type') or ''} {source.get('category') or ''} {source.get('domain') or ''}".lower()
    return "official" in blob or any(
        d in blob for d in ("gob.mx", "usda", "woah", "aphis", "senasica", "tahc", "who.int", "cdc.gov")
    )
