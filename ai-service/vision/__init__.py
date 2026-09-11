"""Pipeline de imagen — observatorio vigente + contrato CNN/OCR."""
from __future__ import annotations

try:
    from .cnn import IMAGE_CLASSES, classify_image
    from .image_hash import hash_salida_captures, perceptual_hash, sha256_file
    from .ocr import ocr_image
    from .observatory import resolve_image_ui, ui_paths
except ImportError:
    from cnn import IMAGE_CLASSES, classify_image
    from image_hash import hash_salida_captures, perceptual_hash, sha256_file
    from ocr import ocr_image
    from observatory import resolve_image_ui, ui_paths

__all__ = [
    "IMAGE_CLASSES",
    "classify_image",
    "ocr_image",
    "perceptual_hash",
    "sha256_file",
    "hash_salida_captures",
    "ui_paths",
    "resolve_image_ui",
]
