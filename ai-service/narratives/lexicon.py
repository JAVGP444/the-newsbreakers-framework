"""Banco de términos editable. Una palabra no es un veredicto. peso ≠ malicia."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_YAML = _ROOT / "config" / "narrative_banks.yaml"

BANK: dict[str, tuple[str, ...]] = {}
CATEGORY_LABEL: dict[str, str] = {}
WEIGHTS: dict[str, int] = {}
STRUCTURES: list[dict[str, Any]] = []
NARRATIVE_SPECS: list[dict[str, Any]] = []
PRINCIPLE = (
    "Una palabra no es el riesgo. El contexto es el riesgo. "
    "El banco marca qué mirar; no declara que una nota sea falsa ni maliciosa. "
    "peso ≠ malicia."
)


def _load_yaml() -> dict[str, Any]:
    if not _YAML.is_file():
        return {}
    try:
        data = yaml.safe_load(_YAML.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def yaml_term_rows() -> list[dict[str, Any]]:
    data = _load_yaml()
    rows = []
    cats = data.get("categories") or {}
    for cat, spec in cats.items():
        if not isinstance(spec, dict):
            continue
        label = str(spec.get("label") or cat)
        weight = int(spec.get("weight") or 2)
        for term in spec.get("terms") or []:
            text = str(term or "").strip()
            if not text:
                continue
            rows.append(
                {
                    "term": text,
                    "category": str(cat),
                    "label": label,
                    "weight": weight,
                    "active": 1,
                }
            )
    return rows


def _apply_yaml() -> None:
    data = _load_yaml()
    principle = str(data.get("principle") or "").strip()
    global PRINCIPLE
    if principle:
        PRINCIPLE = " ".join(principle.split())
    BANK.clear()
    CATEGORY_LABEL.clear()
    WEIGHTS.clear()
    STRUCTURES.clear()
    NARRATIVE_SPECS.clear()
    cats = data.get("categories") or {}
    for cat, spec in cats.items():
        if not isinstance(spec, dict):
            continue
        terms = tuple(str(t).strip() for t in (spec.get("terms") or []) if str(t).strip())
        if not terms:
            continue
        key = str(cat)
        BANK[key] = terms
        CATEGORY_LABEL[key] = str(spec.get("label") or key)
        WEIGHTS[key] = int(spec.get("weight") or 2)
    for item in data.get("structures") or []:
        if isinstance(item, dict) and item.get("id"):
            STRUCTURES.append(dict(item))
    for item in data.get("narratives") or []:
        if isinstance(item, dict) and item.get("id"):
            NARRATIVE_SPECS.append(dict(item))
    if not BANK:
        BANK["salud_animal"] = ("brote", "outbreak", "caso")
        CATEGORY_LABEL["salud_animal"] = "Eventos sanitarios"
        WEIGHTS["salud_animal"] = 2


def apply_term_rows(rows: list[dict[str, Any]] | None) -> None:
    """Sustituye el banco en memoria con filas activas de SQLite."""
    active = [r for r in (rows or []) if int(r.get("active") if r.get("active") is not None else 1)]
    if not active:
        _apply_yaml()
        return
    grouped: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    weights: dict[str, int] = {}
    for row in active:
        cat = str(row.get("category") or "").strip()
        term = str(row.get("term") or "").strip()
        if not cat or not term:
            continue
        grouped.setdefault(cat, [])
        if term not in grouped[cat]:
            grouped[cat].append(term)
        labels[cat] = str(row.get("label") or labels.get(cat) or cat)
        try:
            weights[cat] = int(row.get("weight") or weights.get(cat) or 2)
        except (TypeError, ValueError):
            weights[cat] = weights.get(cat) or 2
    if not grouped:
        _apply_yaml()
        return
    BANK.clear()
    CATEGORY_LABEL.clear()
    WEIGHTS.clear()
    for cat, terms in grouped.items():
        BANK[cat] = tuple(terms)
        CATEGORY_LABEL[cat] = labels.get(cat) or cat
        WEIGHTS[cat] = max(1, min(5, int(weights.get(cat) or 2)))


def narrative_specs() -> list[dict[str, Any]]:
    if not NARRATIVE_SPECS:
        _apply_yaml()
    return list(NARRATIVE_SPECS)


def term_weight(category: str) -> int:
    try:
        return max(1, min(5, int(WEIGHTS.get(category) or 2)))
    except (TypeError, ValueError):
        return 2


_apply_yaml()
