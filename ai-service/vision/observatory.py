"""Rutas de la UI visual del observatorio vigente."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import (
    CANONICAL_DASHBOARD,
    LAUNCHER_BAT,
    PROJECT_ROOT,
    SALIDA_DIR,
    VISUAL_DASHBOARD,
)

# Lo que el usuario debe abrir HOY (no el mapa de 3 pestañas).
CANONICAL_UI = CANONICAL_DASHBOARD
MAP_ONLY_UI = VISUAL_DASHBOARD


def ui_paths() -> dict[str, Any]:
    return {
        "project_root": str(PROJECT_ROOT),
        "canonical_dashboard": str(CANONICAL_UI),
        "canonical_exists": CANONICAL_UI.is_file(),
        "map_observatory": str(MAP_ONLY_UI),
        "map_exists": MAP_ONLY_UI.is_file(),
        "how_to_open": (
            f"Doble clic en {CANONICAL_UI} "
            "o ejecuta ★ THE NEWSBREAKERS.bat (abre el dashboard canónico)."
        ),
        "regenerate_canonical": "★ THE NEWSBREAKERS.bat solo-dashboard",
        "regenerate_map": "★ THE NEWSBREAKERS.bat solo-visual",
        "launcher": str(LAUNCHER_BAT),
        "salida": str(SALIDA_DIR),
        "note": (
            "observatorio_visual.html es Mapa+Gráficas+Dominio (presentación). "
            "urls_enfermedades_dashboard.html es la UI completa "
            "(Panorama, YouTube, Social, Evidencia)."
        ),
    }


def resolve_image_ui() -> Path:
    if CANONICAL_UI.is_file():
        return CANONICAL_UI
    if MAP_ONLY_UI.is_file():
        return MAP_ONLY_UI
    return CANONICAL_UI
