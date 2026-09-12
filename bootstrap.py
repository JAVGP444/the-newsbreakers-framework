"""Rutas del framework y del proyecto vigente (observatorio Excel / imágenes).

Los directorios con guion (ai-service, evidence-service) no son paquetes
importables; este módulo los añade a sys.path para imports planos.

Ubicación (Escritorio — carpetas hermanas, no anidar):

    Proyecto vigente:  C:\\Users\\javie\\OneDrive\\Escritorio\\Generador_Excel_Enfermedades
    Framework:         C:\\Users\\javie\\OneDrive\\Escritorio\\the-newsbreakers-framework

    Obsoleto (no es fuente de verdad):
                       C:\\Users\\javie\\OneDrive\\Escritorio\\the-newsbreakers
                       (verificador FastAPI + Next.js)

Override:

    $env:TNB_DEMO_ROOT = "C:\\Users\\javie\\OneDrive\\Escritorio\\Generador_Excel_Enfermedades"

Uso:
    from bootstrap import ensure_paths
    ensure_paths()
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

from config.paths import app_home, bundle_root  # noqa: E402

_HOME = app_home()

_DEFAULT_PROJECT = FRAMEWORK_ROOT.parent / "Generador_Excel_Enfermedades"
PROJECT_ROOT = Path(
    os.environ.get("TNB_DEMO_ROOT")
    or os.environ.get("TNB_PROJECT_ROOT")
    or _DEFAULT_PROJECT
).resolve()
DEMO_ROOT = PROJECT_ROOT  # alias histórico

NEWSBREAKERS_PKG = PROJECT_ROOT / "newsbreakers"
DATOS_DIR = PROJECT_ROOT / "datos"
SALIDA_DIR = PROJECT_ROOT / "salida"
DICT_DIR = NEWSBREAKERS_PKG / "dictionaries"
SOURCE_REGISTRY = DATOS_DIR / "source_registry.yaml"
_GENERADOR_DISEASES = DICT_DIR / "diseases.yaml"
_BUNDLED_DISEASES = FRAMEWORK_ROOT / "config" / "diseases.yaml"
DISEASES_YAML = _GENERADOR_DISEASES if _GENERADOR_DISEASES.is_file() else _BUNDLED_DISEASES
WATCHLIST_YAML = FRAMEWORK_ROOT / "config" / "watchlist.yaml"
EXCEL_PKG = PROJECT_ROOT / "excel_enfermedades"

# El verificador viejo ya no es la UI, pero SÍ se reutilizan NLP/LLM (claim_extractor, ai_verifier).
LEGACY_REPO = FRAMEWORK_ROOT.parent / "the-newsbreakers"
LEGACY_API = LEGACY_REPO / "api"
CONFIG_DIR = DATOS_DIR
REPO_ROOT = PROJECT_ROOT
GENERADOR_SQLITE = DATOS_DIR / "newsbreakers" / "newsbreakers.db"
CNN_DIR = bundle_root() / "models" / "cnn"
CNN_WEIGHTS = CNN_DIR / "vision_cnn_v1.pt"
CNN_DATASET_DIR = CNN_DIR / "dataset"
CNN_CLASSES = (
    "OFFICIAL_DOCUMENT",
    "NEWS_SCREENSHOT",
    "SOCIAL_MEDIA",
    "MEME",
    "INFOGRAPHIC",
    "ANIMAL_HEALTH_CONTENT",
    "PHOTOGRAPH",
    "POTENTIALLY_MANIPULATED",
)

# OCR real (si existe la carpeta hermana de análisis visual)
_WEB_ANALIZADO = FRAMEWORK_ROOT.parent / "WEB analizado vs code" / "src"
OCR_STUDIO_SRC = Path(os.environ.get("TNB_OCR_SRC", _WEB_ANALIZADO)).resolve()

CANONICAL_DASHBOARD = SALIDA_DIR / "urls_enfermedades_dashboard.html"
VISUAL_DASHBOARD = SALIDA_DIR / "observatorio_visual.html"
LAUNCHER_BAT = PROJECT_ROOT / "★ THE NEWSBREAKERS.bat"

DATA_DIR = _HOME / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = PROCESSED_DIR / "tnb.db"
IMAGES_DIR = _HOME / "storage" / "images"
_GENERADOR_ENF_CFG = PROJECT_ROOT / "enfermedades_config.yaml"
_BUNDLED_ENF_CFG = FRAMEWORK_ROOT / "config" / "enfermedades_config.yaml"
ENFERMEDADES_CONFIG = _GENERADOR_ENF_CFG if _GENERADOR_ENF_CFG.is_file() else _BUNDLED_ENF_CFG
NARRATIVES_YAML = DICT_DIR / "narratives.yaml"

_PATHS = (
    FRAMEWORK_ROOT,
    FRAMEWORK_ROOT / "ingestion",
    FRAMEWORK_ROOT / "ai-service",
    FRAMEWORK_ROOT / "ai-service" / "nlp",
    FRAMEWORK_ROOT / "ai-service" / "vision",
    FRAMEWORK_ROOT / "ai-service" / "verification",
    FRAMEWORK_ROOT / "ai-service" / "embeddings",
    FRAMEWORK_ROOT / "ai-service" / "narratives",
    FRAMEWORK_ROOT / "evidence-service",
    FRAMEWORK_ROOT / "workers",
    FRAMEWORK_ROOT / "pipeline",
    FRAMEWORK_ROOT / "database",
    PROJECT_ROOT,
    NEWSBREAKERS_PKG.parent,  # para `import newsbreakers`
    EXCEL_PKG.parent,  # para `import excel_enfermedades`
    LEGACY_API,  # claim_extractor / ai_verifier (Ollama)
)


def ensure_paths() -> None:
    for path in _PATHS:
        s = str(path)
        if s not in sys.path:
            sys.path.insert(0, s)
    ocr_src = str(OCR_STUDIO_SRC)
    if OCR_STUDIO_SRC.is_dir() and ocr_src not in sys.path:
        sys.path.append(ocr_src)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "backups").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "cache" / "evidence").mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for label in CNN_CLASSES:
        (CNN_DATASET_DIR / label).mkdir(parents=True, exist_ok=True)
