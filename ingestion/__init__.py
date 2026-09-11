"""Paquete de ingesta (watchlist + RSS + normalización + dedup).

PYTHONPATH: añadir esta carpeta `ingestion/` (o ejecutar desde the-newsbreakers-framework).
El prototipo universitario sigue en Escritorio\\the-newsbreakers\\api — este paquete lo reutiliza (GDELT, RSS).
"""
from __future__ import annotations

from source_catalog import active_sources, load_catalog, select_access_method

__all__ = ["load_catalog", "active_sources", "select_access_method"]
