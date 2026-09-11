"""NER — enfermedades, animales, países, organizaciones, estados.

Diccionarios: newsbreakers/dictionaries/diseases.yaml + entities.yaml.
Sin spaCy en MVP: gazetteer real del observatorio (no una lista de 10 palabras).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import yaml

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import DICT_DIR, DISEASES_YAML, ensure_paths  # noqa: E402

ensure_paths()

try:
    from .relevance import matched_diseases
except ImportError:
    from relevance import matched_diseases

ANIMALS: dict[str, str] = {}
COUNTRIES: dict[str, str] = {}
ORGS: dict[str, str] = {
    "senasica": "SENASICA",
    "woah": "WOAH",
    "omsa": "WOAH",
    "oie": "WOAH",
    "fao": "FAO",
    "who": "WHO",
    "oms": "WHO",
    "paho": "PAHO",
    "ops": "PAHO",
    "cdc": "CDC",
    "usda": "USDA",
    "aphis": "USDA APHIS",
    "wahis": "WAHIS",
    "offlu": "OFFLU",
    "inifap": "INIFAP",
    "sader": "SADER",
    "copeg": "COPEG",
}
STATES: dict[str, str] = {}

ENTITY_KINDS = ("DISEASE", "ANIMAL", "COUNTRY", "ORG", "ORGANIZATION", "LOCATION", "STATE")
MODEL_NAME = "gazetteer_ner"
MODEL_VERSION = "diseases_yaml_v2"

_COUNTRY_ISO = {
    "méxico": "MX",
    "mexico": "MX",
    "estados unidos": "US",
    "united states": "US",
    "usa": "US",
    "eua": "US",
    "guatemala": "GT",
    "colombia": "CO",
    "brasil": "BR",
    "brazil": "BR",
    "argentina": "AR",
    "españa": "ES",
    "spain": "ES",
    "chile": "CL",
    "perú": "PE",
    "peru": "PE",
    "china": "CN",
    "francia": "FR",
    "france": "FR",
    "reino unido": "GB",
    "united kingdom": "GB",
}


def _load_gazetteer() -> None:
    ANIMALS.clear()
    COUNTRIES.clear()
    STATES.clear()
    if DISEASES_YAML.exists():
        data = yaml.safe_load(DISEASES_YAML.read_text(encoding="utf-8")) or {}
        for sp, variants in (data.get("species") or {}).items():
            ANIMALS[str(sp).lower()] = str(sp)
            for v in variants or []:
                ANIMALS[str(v).lower()] = str(sp)
        locs = data.get("locations") or {}
        for st in locs.get("mexico_states") or []:
            STATES[str(st).lower()] = str(st)
        for c in locs.get("countries") or []:
            key = str(c).lower()
            COUNTRIES[key] = _COUNTRY_ISO.get(key, str(c))
    for k, iso in _COUNTRY_ISO.items():
        COUNTRIES.setdefault(k, iso)
    ent_path = DICT_DIR / "entities.yaml"
    if ent_path.exists():
        extra = yaml.safe_load(ent_path.read_text(encoding="utf-8")) or {}
        for name in extra.get("institutions") or []:
            ORGS[str(name).lower()] = str(name).upper() if len(str(name)) <= 12 else str(name)


_load_gazetteer()


def _hits(text: str, vocab: dict[str, str], *, word_boundary: bool = False) -> list[str]:
    import re

    lower = (text or "").lower()
    found: list[str] = []
    seen: set[str] = set()
    for needle, canonical in sorted(vocab.items(), key=lambda kv: -len(kv[0])):
        if not needle or canonical in seen:
            continue
        ok = False
        if word_boundary or len(needle) <= 4:
            ok = re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lower) is not None
        else:
            ok = needle in lower
        if ok:
            seen.add(canonical)
            found.append(canonical)
    return found


def extract_entities(text: str, topic_matches: list[str] | None = None) -> list[dict[str, Any]]:
    diseases = list(topic_matches or []) or matched_diseases(text or "")
    entities: list[dict[str, Any]] = []

    def add(kind: str, value: str) -> None:
        eid = hashlib.sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()[:12]
        entities.append(
            {
                "entity_id": f"ENT-{eid}",
                "kind": kind,
                "value": value,
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
            }
        )

    for value in diseases:
        add("DISEASE", value)
    for value in _hits(text or "", ANIMALS):
        add("ANIMAL", value)
    for value in _hits(text or "", COUNTRIES):
        add("COUNTRY", value)
    for value in _hits(text or "", STATES):
        add("STATE", value)
    for value in _hits(text or "", ORGS, word_boundary=True):
        add("ORG", value)

    disease_animal = {
        "gripe_aviar": "aves",
        "gusano_barrenador": "bovino",
        "fiebre_porcina_clasica": "porcino",
    }
    have_animal = {e["value"] for e in entities if e["kind"] == "ANIMAL"}
    for did in diseases:
        animal = disease_animal.get(did)
        if animal and animal not in have_animal and animal.lower() in (text or "").lower():
            add("ANIMAL", animal)
            have_animal.add(animal)
    return entities
