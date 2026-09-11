"""Embeddings de texto/imagen — pgvector en fases posteriores.

Fase 1: contrato. No se añade sentence-transformers / PyTorch a requirements.
"""
from __future__ import annotations

from typing import Any

TEXT_DIM = 384
IMAGE_DIM = 512
MODEL_NAME = "embeddings"
MODEL_VERSION = "stub_zeros_v0"


def embed_text(_text: str) -> dict[str, Any]:
    return {
        "vector": [0.0] * TEXT_DIM,
        "dim": TEXT_DIM,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "implemented": False,
    }


def embed_image(_path: str) -> dict[str, Any]:
    return {
        "vector": [0.0] * IMAGE_DIM,
        "dim": IMAGE_DIM,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "implemented": False,
    }
