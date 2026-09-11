"""Reentrena la CNN desde models/cnn/dataset (imágenes minadas).

    python -m ai_service.vision.train_cnn

No se ejecuta solo en cada ciclo de minería (demasiado pesado).
Si una clase tiene pocas fotos minadas, se completa con sintéticas.
"""
from __future__ import annotations

import sys
from pathlib import Path

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))

from bootstrap import ensure_paths  # noqa: E402

ensure_paths()

from train_cnn import train  # noqa: E402

if __name__ == "__main__":
    train(use_mined=True)
